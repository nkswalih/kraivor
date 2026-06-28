import asyncio
import os
from typing import cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.api.dependencies.services import get_uow
from app.api.schemas.jobs import JobStatusResponse
from app.application.analysis.commands import StartAnalysisCommand
from app.application.analysis.handler import handle_start_analysis
from app.application.tasks.pipeline import run_full_analysis
from app.core.config import get_settings
from app.core.constants import JobStatus, TriggerType
from app.core.logging import get_logger
from app.dependencies.auth import JWTPayload, get_current_user
from app.infrastructure.db.unit_of_work import UnitOfWork
from app.infrastructure.messaging.producer import EventProducer
from app.infrastructure.storage.s3 import S3Storage

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/files", tags=["files"])


@router.post("/upload", response_model=JobStatusResponse, status_code=201)
async def upload_file(
    workspace_id: str,
    file: UploadFile,
    repo_url: str = "",
    branch: str = "main",
    uow: UnitOfWork = Depends(get_uow),
    user: JWTPayload = Depends(get_current_user),
) -> JobStatusResponse:
    settings = get_settings()

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    contents = await file.read()
    if len(contents) > settings.analysis.max_file_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max {settings.analysis.max_file_size_bytes} bytes",
        )

    job_id = uuid4()
    s3_key = (
        f"uploads/{workspace_id}/{job_id}/{file.filename}"
    )

    storage = S3Storage()
    content_type = file.content_type or "application/octet-stream"
    await storage.upload(s3_key, contents, content_type=content_type)

    ext = os.path.splitext(file.filename)[1].lower()
    language = _ext_to_lang.get(ext, "unknown")

    await uow.file_analyses.save_many([{
        "job_id": job_id,
        "workspace_id": UUID(workspace_id),
        "original_filename": file.filename,
        "file_size_bytes": len(contents),
        "language": language,
        "s3_key": s3_key,
        "id": uuid4(),
    }])

    settings = get_settings()
    cmd = StartAnalysisCommand(
        repo_id=uuid4(),
        workspace_id=UUID(workspace_id),
        triggered_by=UUID(user.sub),
        trigger_type=TriggerType.API,
        repo_url=repo_url or f"file://{file.filename}",
        branch=branch,
        deep_scan=False,
        depth=1,
    )
    await handle_start_analysis(cmd, uow)
    await uow.commit()

    asyncio.create_task(_run_analysis_safe({
        "job_id": str(job_id),
        "repo_id": str(cmd.repo_id),
        "workspace_id": workspace_id,
        "triggered_by": user.sub,
        "trigger_type": TriggerType.API,
        "repo_url": cmd.repo_url,
        "branch": cmd.branch,
        "deep_scan": False,
        "depth": 1,
    }))

    job = await uow.jobs.get_by_id(job_id)
    return _job_to_response(job)


async def _run_analysis_safe(cmd_dict: dict[str, object]) -> None:
    try:
        await run_full_analysis(cmd_dict)
    except Exception:
        logger.exception("file_analysis_task_crashed")
        job_id = cmd_dict.get("job_id")
        if job_id:
            try:
                async with UnitOfWork() as uow:
                    producer = EventProducer()
                    from app.application.analysis.handler import handle_analysis_failure
                    await handle_analysis_failure(
                        UUID(cast(str, job_id)),
                        "init",
                        "File analysis crashed before pipeline started",
                        uow,
                        producer,
                    )
                    await uow.commit()
            except Exception:
                logger.exception("last_resort_failure_update_failed")


def _job_to_response(job: dict[str, object]) -> JobStatusResponse:
    from app.api.routers.jobs import _job_to_response as jtr
    return jtr(job)


_EXT_TO_LANG: dict[str, str] = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".tsx": "typescript", ".jsx": "javascript",
    ".rs": "rust", ".go": "go", ".java": "java",
    ".kt": "kotlin", ".kts": "kotlin",
    ".cs": "csharp", ".fs": "fsharp",
    ".rb": "ruby", ".php": "php",
    ".ex": "elixir", ".exs": "elixir",
    ".swift": "swift", ".scala": "scala",
    ".vue": "vue", ".svelte": "svelte",
    ".css": "css", ".scss": "scss", ".less": "less",
    ".html": "html", ".htm": "html",
    ".json": "json", ".yaml": "yaml", ".yml": "yaml",
    ".md": "markdown", ".txt": "text",
    ".sql": "sql", ".sh": "shell", ".bash": "shell",
    ".dockerfile": "dockerfile", ".tf": "terraform",
    ".toml": "toml", ".ini": "ini", ".cfg": "ini",
}
