import  json
import aio_pika
from  aio_pika import Message, DeliveryMode
from app.config import settings

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
        raise RuntimeError("RabbitMQ channel must be initialized")
    message_body = json.dumps({"event": event_type, "data": payload}).encode()
    await channel.default_exchange.publish(
        Message(body=message_body, delivery_mode=DeliveryMode.PERSISTENT),
        routing_key=QUEUE_NAME,
    )