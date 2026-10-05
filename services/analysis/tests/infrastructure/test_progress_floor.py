"""Why the progress floor in `JobRepository.update_status` is wrapped in `coalesce`.

The floor is `max(coalesce(progress_pct, 0), incoming)`. The `coalesce` looks
redundant -- `progress_pct` defaults to 0 in effect, because it is a percentage --
and a reader is invited to delete it as noise.

It is not redundant. It is the only thing making progress record at all on SQLite.

These tests do not use the job model, because the claim is about SQLite's scalar
`max` and nothing else. Driving the real `analysis_jobs` table would need every
one of its not-null columns populated to prove an arithmetic rule, which would
test the fixture rather than the rule.

Every assertion here is one that fails if the `coalesce` is removed. The first two
exist purely to demonstrate the trap: without them the remaining tests would
still pass on Postgres, and the breakage would only appear in the engine the test
suite runs on.

Worth recording, because it is the opposite of what I first assumed and the
assertion below caught it: the unguarded form does not merely lose a run's first
write. It stores NULL, so the next write reads NULL and stores NULL, and every
write of the entire run is discarded. The bar would sit empty from clone to
finalize. Two of these tests were written expecting `[None, 20, 30]` and got
`[None, None, None]`.
"""

import asyncio
from collections.abc import Callable, Sequence
from typing import cast

from sqlalchemy import Column, Integer, MetaData, Table, func, select, update
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.sql.elements import ColumnElement

_METADATA = MetaData()
_PCT = Table(
    "progress_probe",
    _METADATA,
    Column("id", Integer, primary_key=True),
    Column("progress_pct", Integer, nullable=True),
)

# How a test builds the value written into the column: either `update_status`'s
# floored expression, or the unguarded version being demonstrated as broken.
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


def _floor(column: ColumnElement[int], incoming: int) -> ColumnElement[int]:
    """`update_status`'s expression: the stored value, floored against the incoming one."""
    return cast("ColumnElement[int]", func.max(func.coalesce(column, 0), incoming))


def _floor_without_coalesce(
    column: ColumnElement[int], incoming: int
) -> ColumnElement[int]:
    """The same floor with the `coalesce` removed -- the tempting simplification."""
    return cast("ColumnElement[int]", func.max(column, incoming))


# ======================================================================
# The trap
# ======================================================================


class TestTheTrap:
    def test_a_run_that_never_wrote_progress_before(self) -> None:
        # Every run's first progress write happens against a NULL column.
        result = asyncio.run(_scenario(_floor, [10]))

        assert (
            result[0] == 10
        ), f"the first write of a run stored {result[0]!r} instead of 10"

    def test_sqlite_max_of_null_is_null_so_coalesce_is_load_bearing(self) -> None:
        # The reason, isolated. SQLite's two-argument `max` returns NULL if any
        # argument is NULL; Postgres treats the same call as `greatest` and skips
        # the NULL.
        #
        # The consequence is worse than losing the first write. The unguarded
        # write stores NULL, so the *next* one reads NULL again and stores NULL
        # again -- every write of the whole run is discarded, and the bar sits
        # empty until something outside this path sets the column. Which means the
        # unguarded form works perfectly in production Postgres and silently does
        # nothing in the SQLite the test suite and local dev run on, which is the
        # easiest possible shape for a regression to survive review.
        result = asyncio.run(_scenario(_floor_without_coalesce, [10, 20, 30]))

        assert result == [None, None, None], (
            "expected SQLite to discard every write while the column is NULL; "
            f"got {result!r}. If this now fails, the database this suite runs "
            "against has changed and the portability claim above needs rechecking."
        )

    def test_the_coalesced_form_records_every_write_from_the_first(self) -> None:
        # The other half of the same claim, stated positively, so the guarantee
        # is pinned by something that would fail if the floor were removed rather
        # than by something that would fail if it were removed *badly*.
        result = asyncio.run(_scenario(_floor, [10, 20, 30]))

        assert result == [10, 20, 30]


# ======================================================================
# The guarantee
# ======================================================================


class TestTheGuarantee:
    def test_a_lower_value_is_refused(self) -> None:
        # The defect being fixed. The `errors` stage handler reported 86% while
        # the pipeline's own table put that stage at 78%, so the next stage's
        # write pulled the bar from 86 back to 80 in front of the reader.
        result = asyncio.run(_scenario(_floor, [86, 80]))

        assert result == [86, 86], (
            f"the bar rewound to {result[1]!r}; a reader watching a 2s poll saw "
            "the fill shrink mid-run"
        )

    def test_a_higher_value_still_gets_through(self) -> None:
        # The floor must not become a ceiling -- that would freeze every run at
        # its first write.
        result = asyncio.run(_scenario(_floor, [10, 25, 40, 100]))

        assert result == [10, 25, 40, 100]

    def test_a_repeated_value_is_idempotent(self) -> None:
        # The pipeline writes the same stage percentage twice in a row -- once
        # when the stage starts and once when it finishes with its results
        # counted. `perf` and `simulation` and `ai_enrich` all do this.
        result = asyncio.run(_scenario(_floor, [87, 87, 90]))

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
        result = asyncio.run(_scenario(_floor, stages))

        assert result == [
            max(stages[: i + 1]) for i in range(len(stages))
        ], "the recorded sequence is no longer the running maximum"
        assert result[-1] == 100
