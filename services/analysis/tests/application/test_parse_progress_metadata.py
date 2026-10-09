"""Pin that code-entity totals are available while a job is still running.

`analysis_metadata` holds class, function and endpoint counts, and it is what a
running job's sidebar has to show. It was written exactly once, after the last
file had been parsed. On a repository that takes minutes to scan, that means the
counts were unavailable for the whole of the interesting part of the run.

Two changes make them available early:

  1. `AnalysisMetadataRepository.save` upserts on `job_id`. It used to
     `session.add`, so a second save for the same job inserted a second row and
     turned every later `get_by_job` into a `MultipleResultsFound`, because that
     read uses `scalar_one_or_none`.

  2. `handle_stage_parse` saves the running total as it goes, on a 10-point
     progress cadence, and commits before pushing the progress that announces
     the checkpoint.

The tests reach the database through the metadata repository and the job row
rather than through the handler's locals, so they fail for the original reason.
The ordering test is the one worth reading: asserting only that a total exists
somewhere in the run is not enough, because a total written after the stage
ends would satisfy that too. What matters is that the number is committed before
a reader is told the progress that carries it.
"""

from __future__ import annotations

import asyncio
from typing import cast
from unittest.mock import patch
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.analysis.commands import ProcessStageCommand
from app.application.analysis.handler import handle_stage_parse
from app.domain.contracts.parser import (
    ParsedClass,
    ParsedFile,
    ParsedFunction,
    ParsedRoute,
)
from app.domain.entities.analysis_metadata import AnalysisMetadata
from app.infrastructure.db.repositories.analysis_metadata import (
    AnalysisMetadataRepository,
)
from app.infrastructure.db.unit_of_work import UnitOfWork
from app.infrastructure.messaging.producer import EventProducer
from app.infrastructure.parsers.base import ChainedParser

# ======================================================================
# Parsed-file builders
# ======================================================================


def _file(
    path: str, *, classes: int = 0, functions: int = 0, routes: int = 0
) -> ParsedFile:
    return ParsedFile(
        path=path,
        language="python",
        content="",
        size_bytes=0,
        lines_count=10,
        classes=[
            ParsedClass(name=f"C{i}", line_start=1, line_end=2) for i in range(classes)
        ],
        functions=[
            ParsedFunction(name=f"f{i}", line_start=1, line_end=2)
            for i in range(functions)
        ],
        routes=[
            ParsedRoute(
                path=f"/r{i}", method="GET", handler_name="h", line_start=1, line_end=2
            )
            for i in range(routes)
        ],
    )


class _StubParser:
    """Yields a prepared ParsedFile per input, or raises for a named path."""

    def __init__(self, by_path: dict[str, ParsedFile], fail: set[str] | None = None):
        self._by_path = by_path
        self._fail = fail or set()
        self.requested: list[str] = []

    async def parse(self, file_path: str, content: str) -> ParsedFile:
        self.requested.append(file_path)
        if file_path in self._fail:
            raise ValueError(f"cannot parse {file_path}")
        return self._by_path[file_path]


# ======================================================================
# Fakes that record one ordered event stream
# ======================================================================


class _Recorder:
    """A single ordered log, so ordering between two writers is observable."""

    def __init__(self) -> None:
        self.events: list[tuple[str, object]] = []

    def note(self, kind: str, payload: object = None) -> None:
        self.events.append((kind, payload))

    def of_kind(self, kind: str) -> list[object]:
        return [payload for k, payload in self.events if k == kind]


class _RecordingMetadataRepo:
    def __init__(self, recorder: _Recorder) -> None:
        self._recorder = recorder

    async def save(self, metadata: AnalysisMetadata) -> None:
        self._recorder.note(
            "metadata",
            (metadata.class_count, metadata.function_count, metadata.endpoint_count),
        )


class _FakeJobsRepo:
    def __init__(self, recorder: _Recorder) -> None:
        self._recorder = recorder

    async def get_by_id(self, job_id: object) -> dict[str, object]:
        return {"repo_id": uuid4(), "workspace_id": uuid4()}

    async def update_status(self, *args: object, **kwargs: object) -> None:
        self._recorder.note("progress", kwargs.get("progress_pct"))


class _FakeUow:
    def __init__(self, recorder: _Recorder) -> None:
        self.recorder = recorder
        self.analysis_metadata = _RecordingMetadataRepo(recorder)
        self.jobs = _FakeJobsRepo(recorder)

    async def commit(self) -> None:
        self.recorder.note("commit")


class _FakeSession:
    """Stands in for the session `_push_progress` opens for itself."""

    def __init__(self, recorder: _Recorder) -> None:
        self._recorder = recorder

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, *exc_info: object) -> bool:
        return False

    async def execute(self, stmt: object) -> None:
        self._recorder.note("progress_row_write")

    async def commit(self) -> None:
        self._recorder.note("progress_commit")

    async def rollback(self) -> None:
        return None

    async def close(self) -> None:
        return None


def _fake_session_factory(recorder: _Recorder) -> object:
    def _factory() -> _FakeSession:
        return _FakeSession(recorder)

    return _factory


# ======================================================================
# Helpers
# ======================================================================


async def _run_parse(
    files: list[ParsedFile],
    *,
    n_inputs: int | None = None,
    fail: set[str] | None = None,
    languages: list[str] | None = None,
    frameworks: list[str] | None = None,
) -> _Recorder:
    """Run `handle_stage_parse` over `files`, returning the ordered recorder.

    `n_inputs` lets the caller say how many loop iterations happened, which is
    how a test gets past the every-5-files progress tick without inventing 500
    files.
    """
    recorder = _Recorder()
    by_path = {f.path: f for f in files}
    inputs: list[dict[str, object]] = []
    for i in range(len(by_path) if n_inputs is None else n_inputs):
        path = files[i % len(files)].path if files else "src/x.py"
        inputs.append({"path": path, "content": ""})
    if not inputs:
        inputs = [{"path": "src/x.py", "content": ""}]

    uow = _FakeUow(recorder)
    parser = _StubParser(by_path, fail)

    with patch(
        "app.infrastructure.db.session.async_session_factory",
        _fake_session_factory(recorder),
    ):
        await handle_stage_parse(
            ProcessStageCommand(job_id=uuid4(), stage="parse"),
            cast("ChainedParser", parser),
            cast("UnitOfWork", uow),
            cast("EventProducer", None),
            "/repo",
            inputs,
            languages=languages if languages is not None else [],
            frameworks=frameworks if frameworks is not None else [],
        )

    return recorder


def _totals(recorder: _Recorder) -> list[tuple[int, int, int]]:
    return cast(list[tuple[int, int, int]], recorder.of_kind("metadata"))


def _final_total(recorder: _Recorder) -> tuple[int, int, int]:
    """The last total written.

    Asserted non-empty on its own so that "parse wrote no metadata at all" fails
    with that sentence rather than as an IndexError from indexing the list.
    """
    totals = _totals(recorder)
    assert totals, "parse wrote no metadata during the stage"
    return totals[-1]


# ======================================================================
# 1. Totals are written while parse is still running
# ======================================================================


class TestTotalsAppearBeforeTheStageEnds:
    def test_a_total_is_written_for_a_ten_file_repository(self) -> None:
        recorder = asyncio.run(
            _run_parse([_file(f"f{i}.py", classes=1) for i in range(10)])
        )

        assert _totals(recorder), "no metadata was written during parse"

    def test_the_running_total_is_below_the_final_total(self) -> None:
        """The whole point: an early number, not just a final one.

        Every file yields one class, so a repository of ten has a final total of
        ten. If the only write were the last one there would be nothing smaller
        than that to find.
        """
        recorder = asyncio.run(
            _run_parse([_file(f"f{i}.py", classes=1) for i in range(10)])
        )

        totals = _totals(recorder)

        assert totals[-1] == (10, 0, 0)
        assert any(
            classes < 10 for classes, _, _ in totals
        ), "every write carried the final total, so nothing was written early"

    def test_the_running_total_only_ever_grows(self) -> None:
        recorder = asyncio.run(
            _run_parse([_file(f"f{i}.py", classes=1, functions=2) for i in range(10)])
        )

        classes = [c for c, _, _ in _totals(recorder)]

        assert classes == sorted(classes)

    def test_the_final_total_counts_every_entity(self) -> None:
        recorder = asyncio.run(
            _run_parse(
                [
                    _file("a.py", classes=2, functions=3, routes=1),
                    _file("b.py", classes=1, functions=4, routes=2),
                ],
                n_inputs=10,
            )
        )

        # Two files alternating ten times over: five of each.
        assert _final_total(recorder) == (15, 35, 15)

    def test_a_single_file_repository_still_produces_a_total(self) -> None:
        recorder = asyncio.run(_run_parse([_file("only.py", functions=7)]))

        assert _final_total(recorder) == (0, 7, 0)

    def test_an_unparsable_file_is_not_counted(self) -> None:
        """A parse failure must reduce the totals, not abort the stage."""
        good = [_file(f"f{i}.py", classes=1) for i in range(9)]
        bad = _file("broken.py", classes=99)

        recorder = asyncio.run(
            _run_parse([*good, bad], n_inputs=10, fail={"broken.py"})
        )

        assert _final_total(recorder) == (9, 0, 0)


# ======================================================================
# 2. A job always ends up with a row, even with nothing to count
# ======================================================================


class TestAnEmptyRepositoryStillGetsARow:
    def test_a_repository_with_no_files_still_writes_a_total(self) -> None:
        """The loop body never runs, so the checkpoints inside it never fire.

        Without a write after the loop this job would have no metadata row at all
        and the metadata endpoint would have no answer to give.
        """
        recorder = asyncio.run(_run_parse([]))

        assert _totals(recorder) == [(0, 0, 0)]

    def test_a_file_that_fails_to_parse_still_leaves_a_row(self) -> None:
        recorder = asyncio.run(_run_parse([_file("broken.py")], fail={"broken.py"}))

        assert _totals(recorder) == [(0, 0, 0)]


# ======================================================================
# 3. The cadence is bounded
# ======================================================================


class TestTheWriteCadenceIsBounded:
    def test_writes_are_not_per_file(self) -> None:
        """Parse ticks every five files; writing on every tick would be an
        UPDATE per five files for the whole stage. The cadence is one write per
        ten points of progress, so a long repository cannot turn this into a
        write amplifier.
        """
        files = [_file(f"f{i}.py", classes=1) for i in range(10)]
        recorder = asyncio.run(_run_parse(files, n_inputs=200))

        writes = len(_totals(recorder))

        # 200 iterations tick 40 times, crossing the 25..60 progress range, whose
        # ten-point buckets number at most four.
        assert writes <= 5, f"{writes} metadata writes across 200 files"

    def test_a_short_repository_is_written_once(self) -> None:
        recorder = asyncio.run(_run_parse([_file("only.py")]))

        assert len(_totals(recorder)) == 1


# ======================================================================
# 4. Ordering: committed before the progress that announces it
# ======================================================================


class TestTotalsAreCommittedBeforeTheProgressIsAnnounced:
    def test_a_commit_precedes_the_progress_push_of_that_checkpoint(self) -> None:
        """The ordering is the feature.

        The frontend polls the job row through its own session. A total written
        but not committed, or committed after the progress that mentions it, is
        invisible to exactly the reader who is watching.
        """
        recorder = asyncio.run(
            _run_parse([_file(f"f{i}.py", classes=1) for i in range(10)])
        )

        kinds = [kind for kind, _ in recorder.events]
        first_metadata = kinds.index("metadata")
        first_commit = kinds.index("commit")

        assert (
            first_commit <= first_metadata + 1
        ), "metadata was written but never committed before the next push"

    def test_every_metadata_write_is_followed_by_a_commit(self) -> None:
        recorder = asyncio.run(
            _run_parse([_file(f"f{i}.py", classes=1) for i in range(10)])
        )

        kinds = [kind for kind, _ in recorder.events]
        metadata_at = [i for i, k in enumerate(kinds) if k == "metadata"]

        for position in metadata_at:
            following = kinds[position + 1 :]
            assert (
                "commit" in following
            ), f"metadata write at {position} was never committed"

    def test_the_stage_still_returns_its_metadata_and_parsed_files(self) -> None:
        """The counts are not the stage's product; the parsed files are."""
        parsed = [_file("a.py", classes=2)]
        recorder = _Recorder()
        by_path = {"a.py": parsed[0]}
        uow = _FakeUow(recorder)

        with patch(
            "app.infrastructure.db.session.async_session_factory",
            _fake_session_factory(recorder),
        ):
            metadata, parsed_files = asyncio.run(
                handle_stage_parse(
                    ProcessStageCommand(job_id=uuid4(), stage="parse"),
                    cast("ChainedParser", _StubParser(by_path)),
                    cast("UnitOfWork", uow),
                    cast("EventProducer", None),
                    "/repo",
                    [{"path": "a.py", "content": ""}],
                    languages=["Python"],
                    frameworks=["fastapi"],
                )
            )

        assert metadata == [
            {
                "path": "a.py",
                "language": "python",
                "lines": 10,
                "functions": 0,
                "classes": 2,
                "routes": 0,
                "imports": 0,
                "has_errors": False,
            }
        ]
        assert parsed_files == parsed


# ======================================================================
# 5. The repository upserts rather than inserting a second row
# ======================================================================


class _UpsertSession:
    """Records statements; `rowcount` decides update-against-insert."""

    def __init__(self, rowcount: int) -> None:
        self._rowcount = rowcount
        self.updates: list[dict[str, object]] = []
        self.added: list[object] = []

    async def execute(self, stmt: object) -> _RowCountResult:
        from sqlalchemy.sql import ClauseElement

        params = dict(cast(ClauseElement, stmt).compile().params)
        self.updates.append(params)
        return _RowCountResult(self._rowcount)

    def add(self, model: object) -> None:
        self.added.append(model)


class _RowCountResult:
    def __init__(self, rowcount: int) -> None:
        self.rowcount = rowcount


class TestTheRepositoryUpsertsOnJobId:
    def test_a_first_save_inserts(self) -> None:
        session = _UpsertSession(rowcount=0)

        asyncio.run(
            AnalysisMetadataRepository(cast("AsyncSession", session)).save(
                _metadata(job_id=uuid4(), classes=3)
            )
        )

        assert len(session.added) == 1

    def test_a_second_save_for_the_same_job_only_updates(self) -> None:
        """The failure this prevents.

        `get_by_job` reads with `scalar_one_or_none`, so a duplicate row turns
        every later read of that job into a `MultipleResultsFound`.
        """
        session = _UpsertSession(rowcount=1)
        job_id = uuid4()

        asyncio.run(
            AnalysisMetadataRepository(cast("AsyncSession", session)).save(
                _metadata(job_id=job_id, classes=3)
            )
        )

        assert session.added == [], "a row was inserted when one already existed"

    def test_the_update_targets_the_job_not_a_generated_id(self) -> None:
        """`AnalysisMetadata.id` is a fresh uuid4 per instance, so matching on
        it would never find the existing row."""
        job_id = uuid4()
        session = _UpsertSession(rowcount=1)

        asyncio.run(
            AnalysisMetadataRepository(cast("AsyncSession", session)).save(
                _metadata(job_id=job_id, classes=3)
            )
        )

        params = session.updates[0]
        assert job_id in params.values(), f"update did not carry the job id: {params}"

    def test_the_update_carries_the_new_counts(self) -> None:
        session = _UpsertSession(rowcount=1)

        asyncio.run(
            AnalysisMetadataRepository(cast("AsyncSession", session)).save(
                _metadata(job_id=uuid4(), classes=11, functions=22, endpoints=33)
            )
        )

        params = session.updates[0]
        assert params["class_count"] == 11
        assert params["function_count"] == 22
        assert params["endpoint_count"] == 33

    def test_languages_and_frameworks_are_written(self) -> None:
        session = _UpsertSession(rowcount=1)

        asyncio.run(
            AnalysisMetadataRepository(cast("AsyncSession", session)).save(
                _metadata(
                    job_id=uuid4(), languages=["Python", "Go"], frameworks=["django"]
                )
            )
        )

        params = session.updates[0]
        assert params["languages"] == ["Python", "Go"]
        assert params["frameworks"] == ["django"]


def _metadata(
    *,
    job_id: object,
    classes: int = 0,
    functions: int = 0,
    endpoints: int = 0,
    languages: list[str] | None = None,
    frameworks: list[str] | None = None,
) -> AnalysisMetadata:
    return AnalysisMetadata(
        job_id=cast(UUID, job_id),
        class_count=classes,
        function_count=functions,
        endpoint_count=endpoints,
        languages=languages if languages is not None else [],
        frameworks=frameworks if frameworks is not None else [],
    )
