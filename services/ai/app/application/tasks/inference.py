from app.core.celery_app import celery_app


@celery_app.task(bind=True, queue="ai.inference")
def run_inference(self, user_id: str, message: str, conversation_id: str | None = None):
    import asyncio

    from app.application.chat.chat_service import ChatService

    async def _run():
        svc = ChatService()
        result = await svc.chat(
            user_id=user_id,
            message=message,
            conversation_id=conversation_id,
        )
        return result

    return asyncio.run(_run())
