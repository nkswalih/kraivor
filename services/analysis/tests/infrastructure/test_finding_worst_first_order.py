"""The findings list runs worst-first, because the recommendation card reads row one.

`FindingRepository.get_by_job` -- reached through `UnitOfWork`, the same wiring
the `GET /findings` handler uses -- feeds two surfaces: the findings list and
the sidebar's single-row fetch behind the Highest Priority Recommendation card.
The card asks for exactly one row and treats it as the run's worst active
finding, so the ORDER BY clause -- not the API, and not the frontend -- is what
makes "row one is the worst" true.

Before this, the ordering was `severity.asc()` over a VARCHAR column, and a
string sort ranks severities alphabetically: critical, high, info, low, medium.
That is not the ranking printed on the badge, and a card reading row one under
it could have quoted an `info` finding while a `critical` one sat in the same
run. A severity CASE fixes it, and the tests below are the pin: they insert
findings in an order no one would call worst-first and assert the repository
hands them back worst-first anyway.

The table is created for real rather than mocked, because the claim is about
SQL ordering semantics and the same expression has to rank worst-first on the
engine the suite runs on as it does on Postgres in production. Two dialect
facts make the fixture look the way it does: SQLite accepts the model's
`analysis` schema only as an attached database, so one is attached; and the
jobs table's ARRAY columns have no SQLite rendering, so only
`analysis_results` is created. The job model still has to be registered
before any query runs -- the findings table's foreign key and
`FindingModel.job` both resolve through it -- and `UnitOfWork`'s chain of
repository imports is what registers it.
"""

from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
from sqlalchemy import insert, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.constants import Category, FindingStatus, Severity
from app.infrastructure.db.models.finding import FindingModel
from app.infrastructure.db.unit_of_work import UnitOfWork

# One run, one repository, shared by every test: each test opens its own
# in-memory database, so the ids never collide with data another test sees.
_JOB_ID = uuid4()
_REPO_ID = uuid4()
_WORKSPACE_ID = uuid4()

# What a row under test is: severity, score impact (negative is damage, None
# is unmeasured), and status. Every test writes its rows in the order listed.
Row = tuple[str, float | None, str]

_ACTIVE = str(FindingStatus.ACTIVE)
_DISMISSED = str(FindingStatus.DISMISSED)


@asynccontextmanager
async def _findings_table() -> AsyncGenerator[AsyncSession]:
    """The real findings table, in memory, with the model's schema attached.

    One engine per test, disposed on the way out. The session is yielded open
    so the seeding insert and the repository's select run in the same
    transaction -- the repository must read what the test just wrote.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            await conn.execute(text("ATTACH DATABASE ':memory:' AS analysis"))
            await conn.run_sync(FindingModel.__table__.create)
        async with async_sessionmaker(engine)() as session:
            yield session
    finally:
        await engine.dispose()


async def _seed(session: AsyncSession, rows: Sequence[Row]) -> None:
    """Insert `rows` in exactly the order given.

    The order is deliberately not worst-first: half the point of the tests is
    that the repository must not depend on insertion order matching the
    ranking. `line_start` counts up so a test can tell two otherwise equal
    rows apart after the round trip.
    """
    await session.execute(
        insert(FindingModel),
        [
            {
                "id": uuid4(),
                "job_id": _JOB_ID,
                "repo_id": _REPO_ID,
                "workspace_id": _WORKSPACE_ID,
                "category": str(Category.QUALITY),
                "severity": severity,
                "title": f"{severity} finding",
                "score_impact": impact,
                "line_start": index + 1,
                "status": status,
            }
            for index, (severity, impact, status) in enumerate(rows)
        ],
    )
    await session.flush()


@pytest.mark.asyncio
async def test_orders_severities_worst_first_and_not_alphabetically() -> None:
    """critical, high, medium, low, info -- the order the badge ranks them.

    Alphabetical would put `info` ahead of `medium`, insertion order would put
    `low` first. Both fail this assertion, which is the point: the ranking is
    declared in the statement, not inherited from either accident.
    """
    async with _findings_table() as session:
        await _seed(
            session,
            [
                ("low", -1.0, _ACTIVE),
                ("info", -0.1, _ACTIVE),
                ("medium", -4.0, _ACTIVE),
                ("critical", -15.0, _ACTIVE),
                ("high", -8.0, _ACTIVE),
            ],
        )

        async with UnitOfWork(session) as uow:
            findings, _ = await uow.findings.get_by_job(_JOB_ID)

        assert [f.severity for f in findings] == [
            Severity.CRITICAL,
            Severity.HIGH,
            Severity.MEDIUM,
            Severity.LOW,
            Severity.INFO,
        ]


@pytest.mark.asyncio
async def test_orders_by_damage_within_one_severity() -> None:
    """Same badge label, different cost: the larger deduction goes first.

    Rules emit negative `score_impact`, so -15 costs more than -0.5 and plain
    ascending order is already worst-first. The test pins that the tiebreak is
    the damage and not the line number or the insertion order.
    """
    async with _findings_table() as session:
        await _seed(
            session,
            [
                ("high", -0.5, _ACTIVE),
                ("high", -15.0, _ACTIVE),
                ("high", -8.0, _ACTIVE),
            ],
        )

        async with UnitOfWork(session) as uow:
            findings, _ = await uow.findings.get_by_job(_JOB_ID)

        assert [f.score_impact for f in findings] == [-15.0, -8.0, -0.5]


@pytest.mark.asyncio
async def test_unmeasured_damage_ranks_behind_measured_damage() -> None:
    """NULL `score_impact` means nobody measured one -- not "worst on the run".

    The coalesce is what makes that answer portable. SQLite sorts NULLs first
    under ASC and Postgres sorts them last, so without it the same run would
    open on a different finding depending on which engine served it. The rows
    are told apart by their line numbers, because the domain mapper normalises
    a NULL impact to 0.0 and the assertion is about order, not normalisation.
    """
    async with _findings_table() as session:
        await _seed(
            session,
            [
                ("high", None, _ACTIVE),
                ("high", -2.0, _ACTIVE),
            ],
        )

        async with UnitOfWork(session) as uow:
            findings, _ = await uow.findings.get_by_job(_JOB_ID)

        # Row two (the measured -2.0) sorts first; row one (unmeasured) after.
        assert [f.line_start for f in findings] == [2, 1]


@pytest.mark.asyncio
async def test_limit_one_returns_the_single_worst_finding() -> None:
    """The card's fetch: one row, and it is the one the badge would rank first.

    Two criticals share the top badge, and the one that costs more score is
    the later of the two in the table -- so this fails if row one is chosen by
    line order alone. `total` still counts the whole active run: the card may
    say how much there is to get through, and that number must not shrink to
    the page.
    """
    async with _findings_table() as session:
        await _seed(
            session,
            [
                ("critical", -0.5, _ACTIVE),
                ("medium", -4.0, _ACTIVE),
                ("info", -0.1, _ACTIVE),
                ("critical", -15.0, _ACTIVE),
            ],
        )

        async with UnitOfWork(session) as uow:
            findings, total = await uow.findings.get_by_job(_JOB_ID, limit=1)

        assert [f.severity for f in findings] == [Severity.CRITICAL]
        assert [f.score_impact for f in findings] == [-15.0]
        assert total == 4


@pytest.mark.asyncio
async def test_a_dismissed_finding_is_no_longer_the_worst_finding() -> None:
    """Dismissal is a reviewer's decision and the card must not overrule it.

    The critical row has been dismissed, so the default active-only page opens
    on the low one; asking for dismissed rows brings it back, still worst-first.
    """
    async with _findings_table() as session:
        await _seed(
            session,
            [
                ("critical", -15.0, _DISMISSED),
                ("low", -1.0, _ACTIVE),
            ],
        )

        async with UnitOfWork(session) as uow:
            active_only, _ = await uow.findings.get_by_job(_JOB_ID)
            with_dismissed, _ = await uow.findings.get_by_job(
                _JOB_ID, include_dismissed=True
            )

        assert [f.severity for f in active_only] == [Severity.LOW]
        assert [f.severity for f in with_dismissed] == [
            Severity.CRITICAL,
            Severity.LOW,
        ]
