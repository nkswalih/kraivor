import logging
from confluent_kafka import Producer
from django.conf import settings

logger = logging.getLogger(__name__)

_producer: Producer | None = None


def get_producer() -> Producer | None:
    global _producer
    if _producer is None:
        bootstrap_servers = getattr(
            settings, "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
        )
        if not bootstrap_servers:
            logger.warning(
                "kafka.producer.disabled",
                extra={"reason": "KAFKA_BOOTSTRAP_SERVERS not set"},
            )
            return None
        try:
            conf = {
                "bootstrap.servers": bootstrap_servers,
                "client.id": "identity-producer",
                "acks": "all",
                "compression.type": "snappy",
                "retries": 3,
                "retry.backoff.ms": 500,
            }
            _producer = Producer(conf)
            logger.info(
                "kafka.producer.initialized",
                extra={"bootstrap.servers": bootstrap_servers},
            )
        except Exception as exc:
            logger.error("kafka.producer.init_failed", extra={"error": str(exc)})
            return None
    return _producer
