import asyncio
import json
import logging

import aio_pika
from aio_pika.abc import AbstractIncomingMessage
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import ActivityLog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

QUEUE_NAME = "todo_events"


async def handle_message(message: AbstractIncomingMessage) -> None:
    async with message.process():
        body = json.loads(message.body.decode())
        event_id = body.get("event_id")
        event_type = body.get("event")
        data = body.get("data", {})

        logger.info("Received event: %s | event_id: %s", event_type, event_id)

        async with AsyncSessionLocal() as session:
            existing = await session.execute(
                select(ActivityLog).where(ActivityLog.event_id == event_id)
            )
            if existing.scalar_one_or_none() is not None:
                logger.info("Event %s already processed, skipping (idempotent)", event_id)
                return

            log_entry = ActivityLog(
                event_id=event_id,
                event_type=event_type,
                todo_id=data["todo_id"],
                user_id=data["user_id"],
                title=data["title"],
            )
            session.add(log_entry)

            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                logger.info("Event %s was inserted concurrently, skipping", event_id)
                return

        logger.info("Saved activity_log entry for event_id=%s", event_id)


async def main() -> None:
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue(QUEUE_NAME, durable=True)

        logger.info("Consumer started, waiting for messages on '%s'...", QUEUE_NAME)
        await queue.consume(handle_message)

        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())