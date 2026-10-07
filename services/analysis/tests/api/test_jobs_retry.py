"""POST /jobs/{id}/retry: claiming a failed run for a resume.

The endpoint's contract is one pipeline per failed run no matter how the
clicks race: three machine-readable refusals the client acts on differently
(unknown job / not failed / no saved position), an atomic claim so exactly
one concurrent retry wins, and a launched pipeline carrying `resume: True`.
"""

import asyncio
from collections.abc import Generator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.main import create_app
from app.dependencies.auth import JWTPayload


@pytest.fixture
def app() -> FastAPI:
    return create_app()


@pytest.fixture
def app_with_auth_override(app: FastAPI) -> Generator[FastAPI]:
    app.dependency_overrides = {}
    from app.dependencies.auth import get_current_user

    async def mock_user() -> JWTPayload:
        return JWTPayload(
            sub="user-123", workspace_ids=["ws-123"], email="test@example.com"
        )

    app.dependency_overrides[get_current_user] = mock_user
    yield app
    app.dependency_overrides = {}


def _job(status: str = "failed") -> dict[str, object]:
    """Every key `_job_to_response` and the endpoint itself read."""
    return {
        "id": uuid4(),
        "repo_id": uuid4(),
        "workspace_id": uuid4(),
        "triggered_by": uuid4(),
        "trigger_type": "manual",
        "repo_url": "https://github.com/acme/app",
        "branch": "main",
        "deep_scan": True,
        "depth": 1,
        "simulate_users": None,
        "status": status,
        "progress_pct": 78,
        "progress_message": "Failed at stage: dead_code",
        "total_files": 100,
        "total_lines": 5000,
        "total_findings": 12,
        "critical_count": 1,
        "high_count": 2,
        "medium_count": 3,
        "low_count": 4,
        "overall_score": None,
        "blocked_by": [],
        "engine_statuses": {"dead_code": "failed"},
        "error_message": "dead_code exploded",
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
        "started_at": datetime(2026, 1, 1, tzinfo=UTC),
        "completed_at": datetime(2026, 1, 2, tzinfo=UTC),
        "languages_detected": None,
        "language_breakdown": None,
    }


def _overrides(app: FastAPI, mock_uow: object, *, user: bool = True) -> None:
    app.dependency_overrides = {}
    from app.api.dependencies.services import get_uow
    from app.dependencies.auth import get_current_user

    app.dependency_overrides[get_uow] = lambda: mock_uow  # type: ignore[assignment]
    if user:
        async def mock_user() -> JWTPayload:
            return JWTPayload(
                sub="user-123", workspace_ids=["ws-123"], email="test@example.com"
            )

        app.dependency_overrides[get_current_user] = mock_user


def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
class TestRetryEndpoint:
    async def test_unknown_job_is_404(self, app_with_auth_override, mocker) -> None:
        app = app_with_auth_override
        mock_uow = mocker.AsyncMock()
        mock_uow.jobs.get_by_id.return_value = None
        _overrides(app, mock_uow)

        async with _client(app) as client:
            response = await client.post(f"/api/v1/jobs/{uuid4()}/retry")

        assert response.status_code == 404

    async def test_requires_auth(self, app: FastAPI) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/api/v1/jobs/{uuid4()}/retry")

        assert response.status_code == 401

    async def test_a_job_that_is_not_failed_refuses_before_planning(
        self, app_with_auth_override, mocker
    ) -> None:
        # The page's poll is about to show this run alive again; starting a
        # second pipeline because it was retried elsewhere would be the wrong
        # reaction, and no checkpoint read is needed to know the difference.
        app = app_with_auth_override
        mock_uow = mocker.AsyncMock()
        mock_uow.jobs.get_by_id.return_value = _job(status="completed")
        _overrides(app, mock_uow)
        plan = mocker.patch("app.api.routers.jobs.plan_resume")

        async with _client(app) as client:
            response = await client.post(f"/api/v1/jobs/{uuid4()}/retry")

        assert response.status_code == 409
        assert response.json()["detail"] == "not_failed"
        plan.assert_not_called()

    async def test_a_failed_job_without_a_saved_position_is_409(
        self, app_with_auth_override, mocker
    ) -> None:
        # Runs failed before this feature existed, or whose container was
        # recreated since. The client answers `no_checkpoint` by starting a
        # fresh analysis -- the pre-resume behaviour, still honest here.
        app = app_with_auth_override
        mock_uow = mocker.AsyncMock()
        mock_uow.jobs.get_by_id.return_value = _job()
        _overrides(app, mock_uow)
        mocker.patch("app.api.routers.jobs.plan_resume", return_value=None)

        async with _client(app) as client:
            response = await client.post(f"/api/v1/jobs/{uuid4()}/retry")

        assert response.status_code == 409
        assert response.json()["detail"] == "no_checkpoint"
        mock_uow.jobs.queue_if_failed.assert_not_awaited()

    async def test_losing_the_claim_race_is_409_and_launches_nothing(
        self, app_with_auth_override, mocker
    ) -> None:
        # Two clicks, two requests: the first flips failed->queued, the
        # second's guarded UPDATE matches no row. One pipeline, ever.
        app = app_with_auth_override
        mock_uow = mocker.AsyncMock()
        mock_uow.jobs.get_by_id.return_value = _job()
        _overrides(app, mock_uow)
        mocker.patch("app.api.routers.jobs.plan_resume", return_value="dead_code")
        mock_uow.jobs.queue_if_failed.return_value = False
        launch = mocker.patch("app.api.routers.jobs._run_analysis_safe")

        async with _client(app) as client:
            response = await client.post(f"/api/v1/jobs/{uuid4()}/retry")

        assert response.status_code == 409
        assert response.json()["detail"] == "already_queued"
        launch.assert_not_called()

    async def test_happy_path_claims_commits_and_launches_a_resume(
        self, app_with_auth_override, mocker
    ) -> None:
        app = app_with_auth_override
        job = _job()
        mock_uow = mocker.AsyncMock()
        mock_uow.jobs.get_by_id.return_value = job
        _overrides(app, mock_uow)
        mocker.patch("app.api.routers.jobs.plan_resume", return_value="dead_code")
        mock_uow.jobs.queue_if_failed.return_value = True

        launched: dict[str, object] = {}

        async def _fake_run(cmd_dict: dict[str, object]) -> None:
            launched.update(cmd_dict)

        mocker.patch("app.api.routers.jobs._run_analysis_safe", _fake_run)

        async with _client(app) as client:
            response = await client.post(f"/api/v1/jobs/{job['id']}/retry")
            # The endpoint schedules the pipeline with asyncio.create_task;
            # one tick lets it run against the patched function.
            await asyncio.sleep(0)

        assert response.status_code == 200
        data = response.json()
        # The response reflects the claim the transaction just wrote: status
        # flipped, failure traces cleared, position named.
        assert data["status"] == "queued"
        assert data["progress_message"] == "Resuming from dead_code..."
        assert data["error_message"] is None
        # progress_pct is deliberately untouched -- it holds the percentage
        # the run reached, which is where the resume continues from.
        assert data["progress_pct"] == 78.0

        mock_uow.jobs.queue_if_failed.assert_awaited_once_with(
            job["id"], progress_message="Resuming from dead_code..."
        )
        mock_uow.commit.assert_awaited_once()

        assert launched["resume"] is True
        assert launched["job_id"] == str(job["id"])
        assert launched["repo_url"] == "https://github.com/acme/app"
        assert launched["depth"] == 1
        assert launched["deep_scan"] is True
