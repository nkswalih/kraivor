from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pytest_mock.plugin import MockerFixture

from app.api.main import create_app
from app.application.analysis.commands import ProcessStageCommand
from app.application.analysis.handler import handle_stage_finalize
from app.core.constants import Category, Severity
from app.dependencies.auth import JWTPayload
from app.domain.contracts.storage import AbstractStorage
from app.domain.entities.finding import Finding
from app.domain.entities.report import Report
from app.domain.entities.score import Score
from app.infrastructure.db.unit_of_work import UnitOfWork
from app.infrastructure.messaging.producer import EventProducer


@pytest.fixture
def app() -> FastAPI:
    return create_app()


@pytest.fixture
def app_with_auth_override(app: FastAPI) -> Generator[FastAPI, None, None]:
    async def mock_get_current_user() -> JWTPayload:
        return JWTPayload(
            sub="user-123",
            workspace_ids=["ws-123"],
            email="test@example.com",
        )

    app.dependency_overrides = {}
    from app.dependencies.auth import get_current_user

    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield app
    app.dependency_overrides = {}


@pytest.mark.asyncio
class TestScoreHistoryHandler:
    async def test_saves_score_history_in_finalize(self, mocker: MockerFixture) -> None:
        job_id = uuid4()
        repo_id = uuid4()
        ws_id = uuid4()
        job = {
            "id": job_id,
            "repo_id": repo_id,
            "workspace_id": ws_id,
            "branch": "main",
            "status": "cloning",
            "repo_url": "https://github.com/foo/bar",
            "progress_pct": 0,
        }
        score = Score(
            overall=85,
            performance=80,
            security=90,
            reliability=85,
            maintainability=75,
            devops=70,
        )
        findings: list[Finding] = []
        cmd = ProcessStageCommand(job_id=job_id, stage="finalize")

        uow = mocker.AsyncMock(spec=UnitOfWork)
        uow.score_history = mocker.AsyncMock()
        uow.reports = mocker.AsyncMock()
        uow.jobs = mocker.AsyncMock()

        producer = mocker.AsyncMock(spec=EventProducer)
        storage = mocker.AsyncMock(spec=AbstractStorage)

        report = await handle_stage_finalize(
            cmd=cmd,
            uow=uow,
            producer=producer,
            storage=storage,
            job=job,
            score=score,
            findings=findings,
            languages=["python"],
            total_files=10,
            total_lines=500,
            duration_seconds=42,
        )

        assert isinstance(report, Report)
        uow.score_history.save.assert_awaited_once()
        saved = uow.score_history.save.await_args[0][0]
        assert saved["repo_id"] == repo_id
        assert saved["workspace_id"] == ws_id
        assert saved["overall_score"] == 85
        assert saved["performance_score"] == 80
        assert saved["security_score"] == 90
        assert saved["reliability_score"] == 85
        assert saved["maintainability_score"] == 75
        assert saved["devops_score"] == 70
        assert saved["findings_count"] == 0
        assert saved["job_id"] == job_id

    async def test_saves_score_history_with_none_scores(
        self, mocker: MockerFixture
    ) -> None:
        job_id = uuid4()
        repo_id = uuid4()
        ws_id = uuid4()
        job = {
            "id": job_id,
            "repo_id": repo_id,
            "workspace_id": ws_id,
            "branch": "main",
            "status": "cloning",
            "repo_url": "https://github.com/foo/bar",
            "progress_pct": 0,
        }
        score = Score(overall=None, blocked_by=["security"])
        findings = [
            Finding(
                job_id=job_id,
                repo_id=repo_id,
                workspace_id=ws_id,
                rule_id="SEC-001",
                category=Category.SECURITY,
                severity=Severity.HIGH,
                title="test",
                description="",
                recommendation="",
                enterprise_pattern="",
            )
        ]
        cmd = ProcessStageCommand(job_id=job_id, stage="finalize")

        uow = mocker.AsyncMock(spec=UnitOfWork)
        uow.score_history = mocker.AsyncMock()
        uow.reports = mocker.AsyncMock()
        uow.jobs = mocker.AsyncMock()

        producer = mocker.AsyncMock(spec=EventProducer)
        storage = mocker.AsyncMock(spec=AbstractStorage)

        await handle_stage_finalize(
            cmd=cmd,
            uow=uow,
            producer=producer,
            storage=storage,
            job=job,
            score=score,
            findings=findings,
            languages=["python"],
            total_files=10,
            total_lines=500,
            duration_seconds=42,
        )

        uow.score_history.save.assert_awaited_once()
        saved = uow.score_history.save.await_args[0][0]
        assert saved["overall_score"] == 0  # None maps to 0
        assert saved["findings_count"] == 1


@pytest.mark.asyncio
class TestScoreHistoryAPI:
    async def test_get_score_history_returns_list(
        self, app_with_auth_override: FastAPI, mocker: MockerFixture
    ) -> None:
        repo_id = uuid4()
        mock_uow = mocker.AsyncMock()
        mock_uow.score_history.get_by_repo.return_value = [
            {
                "time": "2025-01-01T00:00:00",
                "overall_score": 85,
                "performance_score": 80,
                "security_score": 90,
                "reliability_score": 85,
                "maintainability_score": 75,
                "devops_score": 70,
                "findings_count": 15,
            },
            {
                "time": "2025-01-02T00:00:00",
                "overall_score": 88,
                "performance_score": 82,
                "security_score": 92,
                "reliability_score": 87,
                "maintainability_score": 78,
                "devops_score": 72,
                "findings_count": 12,
            },
        ]
        app = app_with_auth_override
        app.dependency_overrides = {}
        from app.api.dependencies.services import get_uow

        app.dependency_overrides[get_uow] = lambda: mock_uow
        from app.dependencies.auth import get_current_user

        async def mock_user() -> JWTPayload:
            return JWTPayload(
                sub="user-123",
                workspace_ids=["ws-123"],
                email="test@example.com",
            )

        app.dependency_overrides[get_current_user] = mock_user

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/api/v1/score-history/{repo_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["entries"]) == 2
        assert data["entries"][0]["overall_score"] == 85
        assert data["entries"][1]["overall_score"] == 88

    async def test_get_score_history_respects_limit(
        self, app_with_auth_override: FastAPI, mocker: MockerFixture
    ) -> None:
        repo_id = uuid4()
        mock_uow = mocker.AsyncMock()
        mock_uow.score_history.get_by_repo.return_value = []
        app = app_with_auth_override
        app.dependency_overrides = {}
        from app.api.dependencies.services import get_uow

        app.dependency_overrides[get_uow] = lambda: mock_uow
        from app.dependencies.auth import get_current_user

        async def mock_user() -> JWTPayload:
            return JWTPayload(
                sub="user-123",
                workspace_ids=["ws-123"],
                email="test@example.com",
            )

        app.dependency_overrides[get_current_user] = mock_user

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/api/v1/score-history/{repo_id}?limit=10")

        assert response.status_code == 200
        mock_uow.score_history.get_by_repo.assert_awaited_once_with(repo_id, limit=10)

    async def test_get_score_history_unauthorized(self, app: FastAPI) -> None:
        repo_id = uuid4()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/api/v1/score-history/{repo_id}")

        assert response.status_code == 401
