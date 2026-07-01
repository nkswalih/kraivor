import json
import logging
from aiokafka import AIOKafkaConsumer
from app.core.config import settings
from app.infrastructure.messaging.kafka_handler import handle_event

logger = logging.getLogger(__name__)


async def start_consumer():
    consumer = AIOKafkaConsumer(
        "ai.requests", "ai.results",
        bootstrap_servers=settings.kafka__bootstrap__servers,
        group_id="ai-service",
        value_deserializer=lambda v: json.loads(v.decode()),
        auto_offset_reset="earliest",
    )
    await consumer.start()
    try:
        async for msg in consumer:
            try:
                await handle_event(msg.topic, msg.value)
            except Exception as e:
                logger.error("Error handling Kafka event", exc_info=e)
    finally:
        await consumer.stop()
