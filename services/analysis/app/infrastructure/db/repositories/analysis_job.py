from uuid import UUID

from sqlalchemy import case, func, select, update
from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.expression import SQLColumnExpression

from app.core.constants import EngineStateMap
from app.domain.contracts.repository_provider import AbstractJobRepository
from app.infrastructure.db.models.analysis_job import AnalysisJobModel
from app.infrastructure.db.models.file_analysis import FileAnalysisModel
from app.infrastructure.db.models.score_history import ScoreHistoryModel


def floored_progress(
    column: SQLColumnExpression[int], incoming: int
) -> ColumnElement[int]:
    """The value written into `progress_pct`: the stored percentage, floored.

    Spelled as a CASE rather than `max(a, b)` or `greatest(a, b)` because no
    scalar "larger of two numbers" exists on both engines: SQLite has `max` and
    no `greatest`; Postgres has `greatest` and -- this is what took every run
    down at start -- no two-argument `max` at all, rejecting the statement with
    `function max(integer, integer) does not exist`. The expression before this
    one was chosen while the only engine under test was SQLite, passed every
    test in `test_progress_floor.py`, compiled without complaint, and could not
    execute a single statement on the engine production uses. The CASE compiles
    to plain SQL on both.

    A NULL column -- a run's first write, before anything has been recorded --
    takes the `else` branch: `column > incoming` is UNKNOWN, never TRUE, so the
    incoming value is stored rather than a NULL propagating. That is the
    outcome the previous form needed its `coalesce` for, without a function
    name either engine could disagree about.
    """
    return case((column > incoming, column), else_=incoming)


class JobRepository(AbstractJobRepository):
    """SQLAlchemy implementation of AbstractJobRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, job_data: dict[str, object]) -> dict[str, object]:
        model = AnalysisJobModel(**job_data)
        self._session.add(model)
        await self._session.flush()
        return self._to_dict(model)

    async def get_by_id(self, job_id: UUID) -> dict[str, object] | None:
        stmt = select(AnalysisJobModel).where(
            AnalysisJobModel.id == job_id, AnalysisJobModel.deleted_at.is_(None)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_dict(model) if model else None

    async def update_status(
        self,
        job_id: UUID,
        status: str,
        progress_pct: int | None = None,
        engine_statuses: EngineStateMap | None = None,
        **kwargs: object,
    ) -> None:
        """Update a job's status.

        `progress_pct=None` and `engine_statuses=None` leave those columns
        untouched. The old `progress_pct=0` default meant any caller that forgot
        the argument silently reset progress, which is what made a failed job's
        bar snap from 90% back to 0. Every current caller passes it explicitly,
        so nothing depended on that default.

        `engine_statuses` is an explicit parameter rather than another `**kwargs`
        entry so that "leave it alone" is expressible. Passing it through kwargs
        could not distinguish "not supplied" from "set to None".

        `progress_pct` is floored at whatever the row already holds. The pipeline
        and the stage handlers each keep their own idea of how far along a stage
        is, they are maintained by hand, and they disagree: the handler for
        `errors` reported 86% while the pipeline's own table put that stage at
        78%, so the next stage's write dropped the bar from 86 back to 80 in
        front of the reader. Hand-aligning twelve literals against a table in
        another module fixes today's numbers and leaves nothing stopping the next
        edit from reintroducing it, so the invariant is enforced where every write
        passes through instead.

        The floor lives in `floored_progress`, and its spelling is load-bearing.
        The expression this replaced was `max(coalesce(...), ...)`: correct on
        the SQLite the suite runs on, fatal on Postgres, which has no
        two-argument `max` -- the first status write of every run died there
        with `function max(integer, integer) does not exist`, and no analysis
        could start.
        """
        values: dict[str, object] = {"status": status}
        if progress_pct is not None:
            values["progress_pct"] = floored_progress(
                AnalysisJobModel.progress_pct, progress_pct
            )
        if engine_statuses is not None:
            values["engine_statuses"] = engine_statuses
        values.update(kwargs)
        stmt = (
            update(AnalysisJobModel)
            .where(AnalysisJobModel.id == job_id)
            .values(**values)
        )
        await self._session.execute(stmt)

    async def list_by_repo(
        self, repo_id: UUID, limit: int = 10, offset: int = 0
    ) -> tuple[list[dict[str, object]], int]:
        base = select(AnalysisJobModel).where(
            AnalysisJobModel.repo_id == repo_id, AnalysisJobModel.deleted_at.is_(None)
        )
        count_stmt = select(func.count()).select_from(base.subquery())
        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = (
            base.options(self._list_load_only())
            .order_by(AnalysisJobModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_dict_list(m) for m in result.scalars().all()], total

    async def list_by_workspace(
        self, workspace_id: UUID, limit: int = 10, offset: int = 0
    ) -> tuple[list[dict[str, object]], int]:
        base = select(AnalysisJobModel).where(
            AnalysisJobModel.workspace_id == workspace_id,
            AnalysisJobModel.deleted_at.is_(None),
        )
        count_stmt = select(func.count()).select_from(base.subquery())
        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = (
            base.options(self._list_load_only())
            .order_by(AnalysisJobModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_dict_list(m) for m in result.scalars().all()], total

    async def hard_delete(self, job_id: UUID) -> dict[str, object] | None:
        job = await self.get_by_id(job_id)
        if not job:
            return None

        # These tables have no FK cascade — delete manually
        stmt_del_score = sa_delete(ScoreHistoryModel).where(
            ScoreHistoryModel.job_id == job_id
        )
        await self._session.execute(stmt_del_score)

        stmt_del_files = sa_delete(FileAnalysisModel).where(
            FileAnalysisModel.job_id == job_id
        )
        await self._session.execute(stmt_del_files)

        # Delete the job row — DB ON DELETE CASCADE handles the rest
        stmt_del_job = sa_delete(AnalysisJobModel).where(AnalysisJobModel.id == job_id)
        await self._session.execute(stmt_del_job)

        return job

    async def count_by_workspace(self, workspace_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(AnalysisJobModel)
            .where(
                AnalysisJobModel.workspace_id == workspace_id,
                AnalysisJobModel.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    @staticmethod
    def _list_load_only() -> load_only:
        return load_only(
            AnalysisJobModel.id,
            AnalysisJobModel.repo_id,
            AnalysisJobModel.workspace_id,
            AnalysisJobModel.repo_url,
            AnalysisJobModel.branch,
            AnalysisJobModel.status,
            AnalysisJobModel.overall_score,
            AnalysisJobModel.total_findings,
            AnalysisJobModel.total_files,
            AnalysisJobModel.total_lines,
            AnalysisJobModel.progress_pct,
            AnalysisJobModel.progress_message,
            AnalysisJobModel.blocked_by,
            AnalysisJobModel.engine_statuses,
            AnalysisJobModel.error_message,
            AnalysisJobModel.started_at,
            AnalysisJobModel.completed_at,
            AnalysisJobModel.created_at,
            # Carried in the list projection too, not just the detail one. Both
            # endpoints answer with the same `JobStatusResponse`, so projecting
            # these here only would make the field real on one route and null on
            # the other for the very same completed job. The two columns are a
            # few short strings and a handful of small objects per row, which is
            # cheaper than a schema that lies about half its callers.
            AnalysisJobModel.languages_detected,
            AnalysisJobModel.language_breakdown,
        )

    @staticmethod
    def _to_dict_list(model: AnalysisJobModel) -> dict[str, object]:
        return {
            "id": model.id,
            "repo_id": model.repo_id,
            "workspace_id": model.workspace_id,
            "repo_url": model.repo_url,
            "branch": model.branch,
            "status": model.status,
            "overall_score": model.overall_score,
            "total_findings": model.total_findings,
            "total_files": model.total_files,
            "total_lines": model.total_lines,
            "progress_pct": model.progress_pct,
            "progress_message": model.progress_message,
            "blocked_by": model.blocked_by,
            "engine_statuses": model.engine_statuses,
            "error_message": model.error_message,
            "started_at": model.started_at,
            "completed_at": model.completed_at,
            "created_at": model.created_at,
            "languages_detected": model.languages_detected,
            "language_breakdown": model.language_breakdown,
        }

    @staticmethod
    def _to_dict(model: AnalysisJobModel) -> dict[str, object]:
        return {
            "id": model.id,
            "repo_id": model.repo_id,
            "workspace_id": model.workspace_id,
            "triggered_by": model.triggered_by,
            "trigger_type": model.trigger_type,
            "repo_url": model.repo_url,
            "branch": model.branch,
            "deep_scan": model.deep_scan,
            "depth": model.depth,
            "simulate_users": model.simulate_users,
            "status": model.status,
            "progress_pct": model.progress_pct,
            "progress_message": model.progress_message,
            "total_files": model.total_files,
            "total_lines": model.total_lines,
            "total_findings": model.total_findings,
            "critical_count": model.critical_count,
            "high_count": model.high_count,
            "medium_count": model.medium_count,
            "low_count": model.low_count,
            "overall_score": model.overall_score,
            "performance_score": model.performance_score,
            "security_score": model.security_score,
            "reliability_score": model.reliability_score,
            "maintainability_score": model.maintainability_score,
            "devops_score": model.devops_score,
            "blocked_by": model.blocked_by,
            "engine_statuses": model.engine_statuses,
            "error_message": model.error_message,
            "started_at": model.started_at,
            "completed_at": model.completed_at,
            "duration_seconds": model.duration_seconds,
            "created_at": model.created_at,
            "languages_detected": model.languages_detected,
            "language_breakdown": model.language_breakdown,
        }
