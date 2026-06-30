import json
import uuid
import logging
import aio_pika
from aio_pika import Message, DeliveryMode
from app.config import settings

logger = logging.getLogger(__name__)

connection: aio_pika.RobustConnection | None = None
channel: aio_pika.RobustChannel | None = None

QUEUE_NAME = "todo_events"


async def init_rabbitmq() -> None:
    global connection, channel
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    await channel.declare_queue(QUEUE_NAME, durable=True)


async def close_rabbitmq() -> None:
    if connection:
        await connection.close()


async def publish_event(event_type: str, payload: dict) -> None:
    if channel is None:
        raise RuntimeError("RabbitMQ channel is not initialized")

    event_id = str(uuid.uuid4())
    message_body = json.dumps({
        "event_id": event_id,
        "event": event_type,
        "data": payload,
    }).encode()

    await channel.default_exchange.publish(
        Message(body=message_body, delivery_mode=DeliveryMode.PERSISTENT),
        routing_key=QUEUE_NAME,
    )