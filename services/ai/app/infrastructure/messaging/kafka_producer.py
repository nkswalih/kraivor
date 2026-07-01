class EventProducer:
    def __init__(self):
        self.producer = None

    async def start(self):
        try:
            from aiokafka import AIOKafkaProducer
            from app.core.config import settings
            self.producer = AIOKafkaProducer(
                bootstrap_servers=settings.kafka__bootstrap__servers,
                client_id="ai-service",
            )
            await self.producer.start()
        except ImportError:
            pass

    async def stop(self):
        if self.producer:
            await self.producer.stop()

    async def emit(self, topic: str, key: str, event: dict):
        if self.producer:
            import json
            await self.producer.send(
                topic,
                key=key.encode(),
                value=json.dumps(event).encode(),
            )


_event_producer: EventProducer | None = None


def get_event_producer() -> EventProducer:
    global _event_producer
    if _event_producer is None:
        _event_producer = EventProducer()
    return _event_producer
