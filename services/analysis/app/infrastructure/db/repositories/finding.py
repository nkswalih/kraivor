from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import FindingStatus
from app.domain.contracts.repository_provider import AbstractFindingRepository
from app.domain.entities.finding import Finding
from app.infrastructure.db.models.finding import FindingModel


class FindingRepository(AbstractFindingRepository):
    """SQLAlchemy implementation of AbstractFindingRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_many(self, findings: list[Finding]) -> int:
        models = [self._to_model(f) for f in findings]
        self._session.add_all(models)
        await self._session.flush()
        return len(models)

    async def get_by_job(
        self,
        job_id: UUID,
        category: str | None = None,
        severity: str | None = None,
        include_dismissed: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Finding], int]:
        stmt = select(FindingModel).where(FindingModel.job_id == job_id)
        count_stmt = select(func.count()).select_from(FindingModel).where(
            FindingModel.job_id == job_id
        )

        if not include_dismissed:
            stmt = stmt.where(FindingModel.status == FindingStatus.ACTIVE)
            count_stmt = count_stmt.where(FindingModel.status == FindingStatus.ACTIVE)
        if category:
            stmt = stmt.where(FindingModel.category == category)
            count_stmt = count_stmt.where(FindingModel.category == category)
        if severity:
            stmt = stmt.where(FindingModel.severity == severity)
            count_stmt = count_stmt.where(FindingModel.severity == severity)

        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.order_by(
            FindingModel.severity.asc(),
            FindingModel.line_start.asc(),
        ).offset(offset).limit(limit)

        result = await self._session.execute(stmt)
        findings = [self._to_domain(m) for m in result.scalars().all()]
        return findings, total

    async def get_by_repo(
        self,
        repo_id: UUID,
        category: str | None = None,
        severity: str | None = None,
        include_dismissed: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Finding], int]:
        stmt = select(FindingModel).where(FindingModel.repo_id == repo_id)
        count_stmt = select(func.count()).select_from(FindingModel).where(
            FindingModel.repo_id == repo_id
        )

        if not include_dismissed:
            stmt = stmt.where(FindingModel.status == FindingStatus.ACTIVE)
            count_stmt = count_stmt.where(FindingModel.status == FindingStatus.ACTIVE)
        if category:
            stmt = stmt.where(FindingModel.category == category)
            count_stmt = count_stmt.where(FindingModel.category == category)
        if severity:
            stmt = stmt.where(FindingModel.severity == severity)
            count_stmt = count_stmt.where(FindingModel.severity == severity)

        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.order_by(FindingModel.created_at.desc()).offset(offset).limit(limit)  # type: ignore[attr-defined]

        result = await self._session.execute(stmt)
        findings = [self._to_domain(m) for m in result.scalars().all()]
        return findings, total

    async def dismiss(self, finding_id: UUID) -> None:
        stmt = (
            update(FindingModel)
            .where(FindingModel.id == finding_id)
            .values(status=FindingStatus.DISMISSED)
        )
        await self._session.execute(stmt)

    async def dismiss_many(self, finding_ids: list[UUID]) -> int:
        stmt = (
            update(FindingModel)
            .where(FindingModel.id.in_(finding_ids))  # type: ignore[attr-defined]
            .values(status=FindingStatus.DISMISSED)
        )
        result = await self._session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]

    async def count_by_severity(self, job_id: UUID) -> dict[str, int]:
        stmt = (
            select(FindingModel.severity, func.count())
            .where(FindingModel.job_id == job_id)
            .where(FindingModel.status == FindingStatus.ACTIVE)
            .group_by(FindingModel.severity)
        )
        result = await self._session.execute(stmt)
        return dict(result.all())  # type: ignore[arg-type]

    async def update_ai_fields(
        self, finding_id: UUID, is_ai_enriched: bool, ai_explanation: str,
    ) -> None:
        stmt = (
            update(FindingModel)
            .where(FindingModel.id == finding_id)
            .values(is_ai_enriched=is_ai_enriched, ai_explanation=ai_explanation)
        )
        await self._session.execute(stmt)

    async def count_by_category(self, job_id: UUID) -> dict[str, int]:
        stmt = (
            select(FindingModel.category, func.count())
            .where(FindingModel.job_id == job_id)
            .where(FindingModel.status == FindingStatus.ACTIVE)
            .group_by(FindingModel.category)
        )
        result = await self._session.execute(stmt)
        return dict(result.all())  # type: ignore[arg-type]

    @staticmethod
    def _to_model(finding: Finding) -> FindingModel:
        return FindingModel(
            id=finding.id,
            job_id=finding.job_id,
            repo_id=finding.repo_id,
            workspace_id=finding.workspace_id,
            category=str(finding.category),
            severity=str(finding.severity),
            status=str(finding.status),
            rule_id=finding.rule_id,
            title=finding.title,
            description=finding.description,
            recommendation=finding.recommendation,
            enterprise_pattern=finding.enterprise_pattern,
            file_path=finding.file_path,
            line_start=finding.line_start,
            line_end=finding.line_end,
            code_snippet=finding.code_snippet,
            fix_snippet=finding.fix_snippet,
            score_impact=finding.score_impact,
            rpm_impact=finding.rpm_impact,
            breaks_at_users=finding.breaks_at_users,
            is_ai_enriched=finding.is_ai_enriched,
            ai_explanation=finding.ai_explanation,
        )

    @staticmethod
    def _to_domain(model: FindingModel) -> Finding:
        from app.core.constants import Category, FindingStatus, Severity

        return Finding(
            id=model.id,
            job_id=model.job_id,
            repo_id=model.repo_id,
            workspace_id=model.workspace_id,
            rule_id=model.rule_id or "",
            category=Category(model.category),
            severity=Severity(model.severity),
            status=FindingStatus(model.status) if model.status else FindingStatus.ACTIVE,
            title=model.title,
            description=model.description or "",
            recommendation=model.recommendation or "",
            enterprise_pattern=model.enterprise_pattern or "",
            file_path=model.file_path or "",
            line_start=model.line_start,
            line_end=model.line_end,
            code_snippet=model.code_snippet or "",
            fix_snippet=model.fix_snippet or "",
            score_impact=model.score_impact or 0.0,
            rpm_impact=model.rpm_impact or 0,
            breaks_at_users=model.breaks_at_users,
            is_ai_enriched=model.is_ai_enriched,
            ai_explanation=model.ai_explanation or "",
        )
