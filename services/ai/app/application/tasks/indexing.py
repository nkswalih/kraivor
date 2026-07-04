from app.core.celery_app import celery_app


@celery_app.task(bind=True, queue="ai.indexing", acks_late=True)
def index_repository(self, repo_id: str, workspace_id: str, files: list[dict]):
    import asyncio

    from app.infrastructure.db.database import async_session_factory
    from app.infrastructure.rag.indexer import Indexer

    async def _run():
        indexer = Indexer()
        async with async_session_factory() as session:
            for file in files:
                await indexer.index_file(
                    db_session=session,
                    repo_id=repo_id,
                    workspace_id=workspace_id,
                    file_path=file["path"],
                    content=file["content"],
                    language=file.get("language", ""),
                )

    asyncio.run(_run())
    return {"status": "completed", "repo_id": repo_id, "files": len(files)}


@celery_app.task(bind=True, queue="ai.indexing", acks_late=True)
def index_single_file(self, repo_id: str, workspace_id: str,
                       file_path: str, content: str, language: str):
    import asyncio

    from app.infrastructure.db.database import async_session_factory
    from app.infrastructure.rag.indexer import Indexer

    async def _run():
        indexer = Indexer()
        async with async_session_factory() as session:
            await indexer.index_file(
                db_session=session,
                repo_id=repo_id,
                workspace_id=workspace_id,
                file_path=file_path,
                content=content,
                language=language,
            )

    asyncio.run(_run())
    return {"status": "completed", "file_path": file_path}
