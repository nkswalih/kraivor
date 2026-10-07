"""Why `JobRepository.update_status` writes its progress floor as a CASE.

The floor is `floored_progress`, imported from the repository above. The tests
drive the real expression rather than a local copy of it -- which they did not
do while the expression was wrong twice, in opposite directions.

1. `max(column, incoming)`: SQLite's two-argument max returns NULL when any
   argument is NULL, and a run's first write is always against a NULL column,
   so the write stored NULL, the next write read NULL, and every write of the
   whole run was discarded -- the bar sat empty from clone to finalize. The
   predecessor of this file caught it by expecting `[None, 20, 30]` and
   getting `[None, None, None]`.

2. `max(coalesce(column, 0), incoming)`: correct on SQLite, fatal on Postgres,
   which has no two-argument max at all. Every status write of every run died
   there with `function max(integer, integer) does not exist` and no analysis
   could start. As the file was written, nothing in it could have caught this:
   the form compiles without complaint, SQLite executes it happily, and only a
   Postgres server refuses it.

So the file is now two halves. The behavior half below runs the real
expression on a probe table -- still not the job model, because the claim
there is arithmetic on one nullable column and driving `analysis_jobs` would
need every not-null column populated to prove it, which would test the fixture
instead of the rule. The portability half compiles the statement
`update_status` actually builds, for the Postgres dialect, and pins the shape
that survives both engines: a CASE, whose NULL column falls into the else
branch on its own -- the outcome mistake 1 needed its coalesce for.

Worth recording, because it is how mistake 2 shipped: half-and-half was the
arrangement then too. Every assertion in the predecessor of this file passed
while `func.max(coalesce(...), ...)` sat in the repository, because none of
them asked the engine production uses.
"""

import asyncio
from collections.abc import Callable, Sequence
from uuid import uuid4

from sqlalchemy import Column, Integer, MetaData, Table, select, update
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.sql.elements import ColumnElement

from app.infrastructure.db.models.analysis_job import AnalysisJobModel
from app.infrastructure.db.repositories.analysis_job import floored_progress

_METADATA = MetaData()
_PCT = Table(
    "progress_probe",
    _METADATA,
    Column("id", Integer, primary_key=True),
    Column("progress_pct", Integer, nullable=True),
)

# How a test builds the value written into the column: `update_status`'s own
# `floored_progress`, imported rather than reproduced. The old local copy is
# why mistake 2 above could sit in the repository through a green suite.
_Assignment = Callable[[ColumnElement[int], int], ColumnElement[int]]


def _session_factory() -> AsyncEngine:
    """A fresh in-memory database with one nullable integer column."""
    return create_async_engine("sqlite+aiosqlite:///:memory:")


async def _scenario(assignment: _Assignment, values: Sequence[int]) -> list[int | None]:
    """Apply `values` in order through `assignment`, returning the column after each.

    The starting row holds NULL, which is the state of a job between `create` and
    its first progress write -- the state every run begins in. The `| None` in the
    return type is what that column may hold afterwards, never what a caller may
    write: every value here is a real percentage.
    """
    engine = _session_factory()

    async def run() -> list[int | None]:
        async with engine.begin() as conn:
            await conn.run_sync(_METADATA.create_all)
            await conn.execute(_PCT.insert().values(id=1, progress_pct=None))

        seen: list[int | None] = []
        async with engine.connect() as conn:
            for value in values:
                await conn.execute(
                    update(_PCT)
                    .where(_PCT.c.id == 1)
                    .values(progress_pct=assignment(_PCT.c.progress_pct, value))
                )
                await conn.commit()
                stored: int | None = (
                    await conn.execute(select(_PCT.c.progress_pct))
                ).scalar_one()
                seen.append(stored)
        return seen

    try:
        return await run()
    finally:
        await engine.dispose()


# ======================================================================
# The trap
# ======================================================================


class TestTheTrap:
    def test_the_real_statement_compiles_to_a_case_on_postgres(self) -> None:
        # Mistake 2, pinned at the only level a SQLite suite can reach. The
        # `max(coalesce(...), ...)` form compiled without complaint and
        # executed perfectly here; Postgres refused it server-side on the
        # first status write of every run. Compiling `update_status`'s own
        # statement for the Postgres dialect and pinning the shape is what a
        # revert has to get past.
        stmt = (
            update(AnalysisJobModel)
            .where(AnalysisJobModel.id == uuid4())
            .values(
                status="running",
                progress_pct=floored_progress(AnalysisJobModel.progress_pct, 10),
            )
        )
        sql = str(stmt.compile(dialect=postgresql.dialect()))

        assert "CASE WHEN" in sql, (
            "the progress floor must compile to a CASE on Postgres; max(a, b) "
            "and greatest(a, b) each die on one of the two engines. Compiled "
            f"to:\n{sql}"
        )
        assert "max(" not in sql.lower(), (
            "Postgres has no two-argument max -- this is the exact shape that "
            f"stopped every analysis from starting:\n{sql}"
        )


# ======================================================================
# The first write
# ======================================================================


class TestTheFirstWrite:
    def test_a_run_that_never_wrote_progress_before(self) -> None:
        # Every run's first progress write happens against a NULL column. The
        # CASE takes its else branch there -- `column > incoming` is UNKNOWN,
        # never TRUE -- so the incoming value lands instead of a NULL, and
        # every write after it keeps recording. The `max` form of mistake 1
        # failed exactly here: `[None, None, None]`.
        result = asyncio.run(_scenario(floored_progress, [10, 20, 30]))

        assert result == [10, 20, 30], (
            "every write of a run must record from the first; "
            f"got {result!r}"
        )


# ======================================================================
# The guarantee
# ======================================================================


class TestTheGuarantee:
    def test_a_lower_value_is_refused(self) -> None:
        # The defect being fixed. The `errors` stage handler reported 86% while
        # the pipeline's own table put that stage at 78%, so the next stage's
        # write pulled the bar from 86 back to 80 in front of the reader.
        result = asyncio.run(_scenario(floored_progress, [86, 80]))

        assert result == [86, 86], (
            f"the bar rewound to {result[1]!r}; a reader watching a 2s poll saw "
            "the fill shrink mid-run"
        )

    def test_a_higher_value_still_gets_through(self) -> None:
        # The floor must not become a ceiling -- that would freeze every run at
        # its first write.
        result = asyncio.run(_scenario(floored_progress, [10, 25, 40, 100]))

        assert result == [10, 25, 40, 100]

    def test_a_repeated_value_is_idempotent(self) -> None:
        # The pipeline writes the same stage percentage twice in a row -- once
        # when the stage starts and once when it finishes with its results
        # counted. `perf` and `simulation` and `ai_enrich` all do this.
        result = asyncio.run(_scenario(floored_progress, [87, 87, 90]))

        assert result == [87, 87, 90]

    def test_a_real_run_never_goes_backwards(self) -> None:
        # The whole sequence a real run produces, including the two regressions
        # that shipped. Each pair is asserted as it happened rather than as a
        # property of a sorted copy, so the test fails if a stage is reintroduced
        # that walks the bar backwards.
        stages = [
            10,
            15,
            18,
            25,
            40,
            59,
            50,
            60,
            65,
            75,
            78,
            86,
            80,
            84,
            82,
            84,
            87,
            90,
            93,
            95,
            97,
            98,
            100,
        ]
        result = asyncio.run(_scenario(floored_progress, stages))

        assert result == [
            max(stages[: i + 1]) for i in range(len(stages))
        ], "the recorded sequence is no longer the running maximum"
        assert result[-1] == 100
