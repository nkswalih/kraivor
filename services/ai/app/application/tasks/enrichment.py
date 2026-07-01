import asyncio
from app.core.celery_app import celery_app


@celery_app.task(bind=True, queue="ai.indexing")
def enrich_codebase(self, repo_id: str, workspace_id: str, changed_files: list[str] | None = None):
    from app.infrastructure.rag.indexer import Indexer
    from app.infrastructure.db.database import async_session_factory

    async def _run():
        indexer = Indexer()
        async with async_session_factory() as session:
            for file_path in changed_files or []:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    language = file_path.split(".")[-1] if "." in file_path else ""
                    await indexer.index_file(
                        db_session=session,
                        repo_id=repo_id,
                        workspace_id=workspace_id,
                        file_path=file_path,
                        content=content,
                        language=language,
                    )
                except FileNotFoundError:
                    pass

    asyncio.run(_run())
    return {"status": "completed", "repo_id": repo_id, "files": changed_files}


@celery_app.task(bind=True, queue="ai.indexing")
def enrich_conversation(self, conversation_id: str):
    return {"status": "completed", "conversation_id": conversation_id}
