import asyncio
import os
import tempfile
import zipfile
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.api.dependencies.services import get_uow
from app.api.schemas.jobs import JobStatusResponse
from app.application.analysis.commands import StartAnalysisCommand
from app.application.analysis.handler import handle_start_analysis
from app.application.tasks.pipeline import run_full_analysis
from app.core.config import get_settings
from app.core.constants import TriggerType
from app.core.logging import get_logger
from app.dependencies.auth import JWTPayload, get_current_user
from app.infrastructure.db.unit_of_work import UnitOfWork
from app.infrastructure.git.repository_fetcher import RepositoryFetcher
from app.infrastructure.messaging.producer import EventProducer
from app.infrastructure.storage.s3 import S3Storage

_background_tasks: set[asyncio.Task[None]] = set()

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/files", tags=["files"])


@router.post("/upload", response_model=JobStatusResponse, status_code=201)
async def upload_file(
    workspace_id: str,
    file: UploadFile,
    uow: UnitOfWork = Depends(get_uow),
    user: JWTPayload = Depends(get_current_user),
) -> JobStatusResponse:
    settings = get_settings()

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    if not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="Only .zip archives are supported. Please upload a project zip file.",
        )

    contents = await file.read()
    if len(contents) > settings.analysis.max_file_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max {settings.analysis.max_file_size_bytes} bytes",
        )

    job_id = uuid4()
    extract_dir = os.path.join(
        settings.analysis.ephemeral_path,
        "uploads",
        str(job_id),
    )
    os.makedirs(extract_dir, exist_ok=True)

    zip_path = os.path.join(extract_dir, file.filename)
    with open(zip_path, "wb") as f:
        f.write(contents)

    extracted_root = os.path.join(extract_dir, "src")
    os.makedirs(extracted_root, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extracted_root)
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid or corrupted zip file")

    fetcher = RepositoryFetcher()
    source_files = await fetcher.get_source_files(extracted_root)
    languages = await fetcher.detect_languages(extracted_root)
    loc = await fetcher.count_loc(extracted_root)

    if not source_files:
        raise HTTPException(
            status_code=400,
            detail="No supported source files found in the uploaded archive",
        )

    storage = S3Storage()
    file_analysis_records: list[dict[str, object]] = []

    for sf in source_files:
        rel_path = cast(str, sf["path"])
        content = cast(str, sf.get("content", ""))
        s3_key = f"uploads/{workspace_id}/{job_id}/{rel_path}"

        await storage.upload(
            s3_key,
            content.encode("utf-8"),
            content_type="text/plain",
        )

        file_analysis_records.append(
            {
                "job_id": job_id,
                "workspace_id": UUID(workspace_id),
                "original_filename": rel_path,
                "file_size_bytes": cast(int, sf.get("size_bytes", 0)),
                "language": cast(str, sf.get("language", "unknown")),
                "s3_key": s3_key,
                "id": uuid4(),
            }
        )

    if file_analysis_records:
        await uow.file_analyses.save_many(file_analysis_records)

    cmd = StartAnalysisCommand(
        repo_id=uuid4(),
        workspace_id=UUID(workspace_id),
        triggered_by=UUID(user.sub),
        trigger_type=TriggerType.API,
        repo_url=f"local://{extracted_root}",
        branch="main",
        deep_scan=False,
        depth=1,
    )
    await handle_start_analysis(cmd, uow)
    await uow.commit()

    background_task = asyncio.create_task(
        _run_analysis_safe(
            {
                "job_id": str(job_id),
                "repo_id": str(cmd.repo_id),
                "workspace_id": workspace_id,
                "triggered_by": user.sub,
                "trigger_type": TriggerType.API,
                "repo_url": cmd.repo_url,
                "branch": cmd.branch,
                "deep_scan": False,
                "depth": 1,
            }
        )
    )
    _background_tasks.add(background_task)
    background_task.add_done_callback(lambda t: _background_tasks.discard(t))

    job = await uow.jobs.get_by_id(job_id)
    return _job_to_response(cast(dict[str, object], job))


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


def _job_to_response(job: dict[str, object] | None) -> JobStatusResponse:
    from app.api.routers.jobs import _job_to_response as jtr

    return jtr(cast(dict[str, object], job))
