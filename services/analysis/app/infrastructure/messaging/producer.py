from app.core.config import get_settings


settings = get_settings()
from app.core.logging import get_logger
from app.domain.events import DomainEvent

logger = get_logger(__name__)


class EventProducer:
    """Publishes domain events to the message broker.

    Currently supports Redis pub/sub. Kafka support can be
    added by implementing the same interface.
    """

    def __init__(self, redis_client=None) -> None:
        self._redis = redis_client
        self._kafka_producer = None

    async def publish(self, event: DomainEvent) -> None:
        """Publish a domain event to the message broker."""
        event_data = event.to_dict()

        # Publish to Redis
        if self._redis:
            try:
                import json

                channel = f"events:{event.event_type}"
                await self._redis.publish(channel, json.dumps(event_data))
                logger.info(
                    "event_published",
                    event_type=event.event_type,
                    channel=channel,
                )
            except Exception as e:
                logger.error(
                    "event_publish_failed",
                    event_type=event.event_type,
                    error=str(e),
                )

        # Publish to Kafka (if configured)
        if self._kafka_producer:
            try:
                import json

                topic = settings.kafka.analysis_events_topic
                self._kafka_producer.send(
                    topic,
                    value=event_data,
                    key=str(getattr(event, "job_id", event.event_id)),
                )
                logger.info(
                    "event_published_kafka",
                    event_type=event.event_type,
                    topic=topic,
                )
            except Exception as e:
                logger.error(
                    "kafka_publish_failed",
                    event_type=event.event_type,
                    error=str(e),
                )

    async def close(self) -> None:
        """Close connections to the message broker."""
        if self._kafka_producer:
            self._kafka_producer.flush()
            self._kafka_producer.close()
