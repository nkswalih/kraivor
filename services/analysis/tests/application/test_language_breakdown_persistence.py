"""Pin that the detected language mix reaches the job row.

`analysis_jobs.languages_detected` and `analysis_jobs.language_breakdown` have
existed since migrations 0010 and 0012 and had exactly one writer: none. Clone
computed a per-language line breakdown, rounded to a tenth of a percent, and
returned it in the stage result; nothing persisted it. The report table received
the same values at finalize, so the data was not lost so much as withheld from
every reader until the run ended -- which is the one time a reader watching a job
does not want it.

The clone tests assert on the keywords `update_status` was called with, because
that is the call that reaches the database. Asserting on the handler's internal
arithmetic would pass even if the values were never written anywhere.

The projection tests call the repository's own mappers with a stand-in model and
check the keys that come out. Reading the mapping's source text instead would
pass on a comment that merely mentions a column name.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.api.routers.jobs import _job_to_response
from app.api.schemas import jobs as jobs_schemas

# `LanguageShare` is new here, so it is reached through the module rather than
# imported by name. A module-level `from ... import LanguageShare` would raise
# ImportError against pre-fix source at collection time, which stops the whole
# file from running and hides the other sixteen failures behind one error.
JobStatusResponse = jobs_schemas.JobStatusResponse
from app.application.analysis.commands import ProcessStageCommand
from app.application.analysis.handler import handle_stage_clone
from app.infrastructure.db.models.analysis_job import AnalysisJobModel
from app.infrastructure.db.repositories.analysis_job import JobRepository
from app.infrastructure.db.unit_of_work import UnitOfWork
from app.infrastructure.git.repository_fetcher import RepositoryFetcher
from app.infrastructure.messaging.producer import EventProducer

# ======================================================================
# Fakes
# ======================================================================


class _RecordingJobsRepo:
    """Records every `update_status` call as the exact keyword set used.

    Storing kwargs rather than a merged dict is the point: a test that needs to
    know whether a column was written must not be satisfied by a value that
    arrived some other way.
    """

    def __init__(self, job: dict[str, object]) -> None:
        self.job = job
        self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    async def get_by_id(self, job_id: object) -> dict[str, object]:
        return self.job

    async def update_status(self, *args: object, **kwargs: object) -> None:
        self.calls.append((args, kwargs))


class _FakeUow:
    def __init__(self, jobs: _RecordingJobsRepo) -> None:
        self.jobs = jobs
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class _FakeProducer:
    def __init__(self) -> None:
        self.published: list[object] = []

    async def publish(self, event: object) -> None:
        self.published.append(event)


class _StubDetection:
    """Stands in for FrameworkDetector's result.

    Framework detection is not what these tests are about, and letting the real
    detector read the filesystem would tie them to whatever happens to be in the
    checkout.
    """

    def __init__(self) -> None:
        self.frameworks: list[object] = []
        self.databases: list[object] = []
        self.tools: list[object] = []
        self.infra: list[object] = []

    def to_dict(self) -> dict[str, object]:
        return {"frameworks": [], "databases": [], "tools": [], "infra": []}


class _StubDetector:
    async def detect(self, repo_path: str) -> _StubDetection:
        return _StubDetection()


class _StubFetcher:
    """Serves a fixed file list, so the handler's own arithmetic is what runs."""

    def __init__(self, files: list[dict[str, object]]) -> None:
        self._files = files

    async def detect_languages(self, repo_path: str) -> list[str]:
        return sorted({cast(str, f["language"]) for f in self._files})

    async def get_source_files(self, repo_path: str) -> list[dict[str, object]]:
        return self._files

    async def language_line_counts(self, repo_path: str) -> dict[str, int]:
        """One bucket per language, so `total_lines` and the shares agree.

        Mirrors the real fetcher's contract: the breakdown is derived from this
        single mapping rather than from `get_source_files`, which is what made
        the two totals incomparable before.
        """
        counts: dict[str, int] = {}
        for f in self._files:
            lang = cast(str, f["language"])
            counts[lang] = counts.get(lang, 0) + cast(int, f["lines_count"])
        return counts


# ======================================================================
# Helpers
# ======================================================================


def _files(*specs: tuple[str, int]) -> list[dict[str, object]]:
    return [
        {"path": f"src/{i}.txt", "language": lang, "lines_count": lines}
        for i, (lang, lines) in enumerate(specs)
    ]


async def _clone(files: list[dict[str, object]]) -> _RecordingJobsRepo:
    """Run `handle_stage_clone` against fakes and return the recording repo."""
    jobs = _RecordingJobsRepo(
        {
            "repo_id": uuid4(),
            "workspace_id": uuid4(),
            # `local://` selects the in-process branch, so no git is invoked.
            "repo_url": "local:///repo",
            "depth": 1,
            "branch": "main",
        }
    )

    with patch(
        "app.infrastructure.detection.detector.FrameworkDetector",
        return_value=_StubDetector(),
    ):
        await handle_stage_clone(
            ProcessStageCommand(job_id=uuid4(), stage="clone"),
            cast("UnitOfWork", _FakeUow(jobs)),
            cast("RepositoryFetcher", _StubFetcher(files)),
            cast("EventProducer", _FakeProducer()),
        )

    assert jobs.calls, "clone never wrote to the job row"
    return jobs


def _clone_now(files: list[dict[str, object]]) -> _RecordingJobsRepo:
    return asyncio.run(_clone(files))


def _write_containing(jobs: _RecordingJobsRepo, key: str) -> dict[str, object]:
    """The single `update_status` call whose kwargs include `key`."""
    matching = [kwargs for _, kwargs in jobs.calls if key in kwargs]
    assert matching, f"no update_status call passed {key}; calls were {jobs.calls}"
    return matching[0]


# ======================================================================
# 1. Clone writes the breakdown instead of discarding it
# ======================================================================


class TestClonePersistsTheLanguageMix:
    def test_the_breakdown_is_written_to_the_job_row(self) -> None:
        jobs = _clone_now(_files(("Python", 300), ("Go", 100)))

        kwargs = _write_containing(jobs, "language_breakdown")

        assert kwargs["language_breakdown"] == [
            {"name": "Python", "percentage": 75.0},
            {"name": "Go", "percentage": 25.0},
        ]

    def test_the_language_names_are_written_too(self) -> None:
        jobs = _clone_now(_files(("Rust", 10), ("Python", 5)))

        kwargs = _write_containing(jobs, "languages_detected")

        assert kwargs["languages_detected"] == ["Python", "Rust"]

    def test_the_row_is_written_while_the_job_is_still_cloning(self) -> None:
        """What distinguishes this write from the finalize one.

        Both target the same columns. Only the clone write is early enough for a
        reader watching a running job, so the status argument is what has to be
        checked -- asserting the columns alone would be satisfied by either.
        """
        jobs = _clone_now(_files(("Python", 10)))

        args, kwargs = next((a, k) for a, k in jobs.calls if "language_breakdown" in k)

        assert args[1] == "cloning", "the breakdown was written after cloning ended"
        assert kwargs["progress_pct"] == 10

    def test_the_file_and_line_counts_are_written_in_the_same_call(self) -> None:
        """One write, not two, so the counts and the mix cannot disagree."""
        jobs = _clone_now(_files(("Python", 30), ("Python", 70)))

        kwargs = _write_containing(jobs, "language_breakdown")

        assert kwargs["total_files"] == 2
        assert kwargs["total_lines"] == 100


# ======================================================================
# 2. The values are derived from the repository, not invented
# ======================================================================


class TestTheBreakdownIsRealNotPlaceholder:
    def test_shares_come_from_line_counts_not_input_order(self) -> None:
        """A hardcoded list could not reorder itself by line count.

        Input order is Python, TypeScript, Go, Elixir. By lines the answer is
        Python (500), Elixir (400), TypeScript (300), Go (200), so Elixir has to
        climb two places and Go has to fall to last.
        """
        jobs = _clone_now(
            _files(("Python", 500), ("TypeScript", 300), ("Go", 200), ("Elixir", 400))
        )

        kwargs = _write_containing(jobs, "language_breakdown")
        breakdown = cast(list[dict[str, object]], kwargs["language_breakdown"])

        assert [b["name"] for b in breakdown] == [
            "Python",
            "Elixir",
            "TypeScript",
            "Go",
        ]

    def test_entries_are_sorted_by_share_descending(self) -> None:
        jobs = _clone_now(_files(("A", 1), ("B", 90), ("C", 9)))

        kwargs = _write_containing(jobs, "language_breakdown")
        breakdown = cast(list[dict[str, object]], kwargs["language_breakdown"])

        shares = [cast(float, b["percentage"]) for b in breakdown]
        assert shares == sorted(shares, reverse=True)

    def test_a_single_language_repository_is_all_of_it(self) -> None:
        jobs = _clone_now(_files(("Rust", 12), ("Rust", 8)))

        kwargs = _write_containing(jobs, "language_breakdown")

        assert kwargs["language_breakdown"] == [{"name": "Rust", "percentage": 100.0}]

    def test_an_empty_repository_yields_an_empty_mix_not_an_invented_one(self) -> None:
        jobs = _clone_now([])

        kwargs = _write_containing(jobs, "language_breakdown")

        assert kwargs["language_breakdown"] == []

    def test_a_language_with_no_lines_does_not_divide_by_zero(self) -> None:
        """`sum(...) or 1` in the handler exists for exactly this."""
        jobs = _clone_now(
            [{"path": "README", "language": "Markdown", "lines_count": 0}]
        )

        kwargs = _write_containing(jobs, "language_breakdown")

        assert kwargs["language_breakdown"] == [{"name": "Markdown", "percentage": 0.0}]


# ======================================================================
# 2b. The shares are shares of the total printed beside them
# ======================================================================
#
# `javascript 0.0, shell 0.0, sql 0.0` on a job whose language list named all
# three was the reported defect. Three things produced it: an extension table
# too small to bucket most files, a denominator drawn from a different file set
# than the buckets, and rounding to a tenth of a percent. Each is pinned below,
# because a test that only checked the ordering would pass on any of them.


class TestTheSharesAreCorrect:
    def test_the_shares_add_up_to_the_total_line_count(self) -> None:
        """The denominator has to be the same population as the numerators.

        Before, `total_lines` counted every non-excluded file while the buckets
        counted only files an extension entry mapped, so the printed percentages
        described a fraction of the LINES figure shown next to them.
        """
        jobs = _clone_now(
            _files(("Python", 535), ("TypeScript", 269), ("JSON", 115))
        )

        kwargs = _write_containing(jobs, "language_breakdown")
        breakdown = cast(list[dict[str, object]], kwargs["language_breakdown"])

        assert sum(cast(float, b["percentage"]) for b in breakdown) == pytest.approx(
            100.0, abs=0.05
        )
        assert kwargs["total_lines"] == 919

    def test_a_share_below_a_tenth_of_a_percent_is_not_reported_as_zero(
        self,
    ) -> None:
        """One line in a nine-thousand-line repository is 0.011%, not 0%.

        Rounded to a single decimal -- which is what the code did -- it became
        `0.0`, and the renderer printed "0%" for a language the repository
        demonstrably contains. Two decimals keep it distinct from absence.
        """
        jobs = _clone_now(
            _files(("Python", 8999), ("Shell", 1))
        )

        kwargs = _write_containing(jobs, "language_breakdown")
        breakdown = cast(list[dict[str, object]], kwargs["language_breakdown"])
        shell = next(b for b in breakdown if b["name"] == "Shell")

        assert shell["percentage"] == 0.01
        assert shell["percentage"] != 0.0

    def test_every_bucket_the_fetcher_returns_becomes_a_share(self) -> None:
        """The denominator is exactly the set of buckets, never a superset.

        The old `total_lines` counted every non-excluded file while the buckets
        came from files an extension entry mapped, so `.tf`, `.ini`, `.html`,
        `.css` and extensionless files sat in the total and in no share -- the
        shares then summed to less than 100 while the names listed beside them
        looked complete. The extension table itself is pinned in
        `test_repository_fetcher_language.py`.
        """
        jobs = _clone_now(
            _files(("Python", 90), ("Terraform", 5), ("INI", 5))
        )

        kwargs = _write_containing(jobs, "language_breakdown")
        breakdown = cast(list[dict[str, object]], kwargs["language_breakdown"])

        assert sum(cast(float, b["percentage"]) for b in breakdown) == pytest.approx(
            100.0, abs=0.05
        )

    def test_the_shares_are_ordered_by_lines_not_by_name(self) -> None:
        jobs = _clone_now(_files(("Zsh", 99), ("Python", 1)))

        kwargs = _write_containing(jobs, "language_breakdown")
        breakdown = cast(list[dict[str, object]], kwargs["language_breakdown"])

        assert [b["name"] for b in breakdown] == ["Zsh", "Python"]

    def test_two_decimals_are_carried_to_the_row(self) -> None:
        """Rounding happens where the value is computed, not in the renderer.

        A test asserting only that shares sum to 100 would pass on values
        already collapsed to a tenth, which is the shape that produced "0%".
        """
        jobs = _clone_now(_files(("Python", 7), ("Go", 3), ("Rust", 1)))

        kwargs = _write_containing(jobs, "language_breakdown")
        breakdown = cast(list[dict[str, object]], kwargs["language_breakdown"])
        shares = [cast(float, b["percentage"]) for b in breakdown]

        assert shares == [63.64, 27.27, 9.09]


# ======================================================================
# 3. The API keeps "not measured" distinct from "measured, empty"
# ======================================================================
#
# `null` and `[]` are different answers and a reader has to be able to tell them
# apart: the first means clone has not run yet, the second means it ran and found
# nothing. Coercing the first into the second makes an honest skeleton
# impossible to render.


def _response(job: dict[str, object]) -> JobStatusResponse:
    base: dict[str, object] = {
        "id": uuid4(),
        "repo_id": uuid4(),
        "workspace_id": uuid4(),
        "repo_url": "local:///repo",
        "branch": "main",
        "status": "cloning",
        "progress_pct": 10,
        "progress_message": "cloning",
        "total_findings": 0,
        # `_job_to_response` indexes this one rather than using .get, so a job
        # dict without it would fail before reaching anything under test.
        "created_at": datetime(2026, 1, 1),
    }
    base.update(job)
    return _job_to_response(base)


class TestTheApiDistinguishesUnmeasuredFromEmpty:
    def test_an_unmeasured_mix_stays_null(self) -> None:
        response = _response({})

        assert response.languages_detected is None
        assert response.language_breakdown is None

    def test_a_measured_empty_mix_stays_an_empty_list(self) -> None:
        response = _response({"languages_detected": [], "language_breakdown": []})

        assert response.languages_detected == []
        assert response.language_breakdown == []

    def test_a_measured_mix_is_carried_through(self) -> None:
        response = _response(
            {
                "languages_detected": ["Python", "Go"],
                "language_breakdown": [
                    {"name": "Python", "percentage": 80.0},
                    {"name": "Go", "percentage": 20.0},
                ],
            }
        )

        assert response.languages_detected == ["Python", "Go"]
        assert response.language_breakdown == [
            jobs_schemas.LanguageShare(name="Python", percentage=80.0),
            jobs_schemas.LanguageShare(name="Go", percentage=20.0),
        ]

    def test_a_breakdown_holding_unknown_keys_still_validates(self) -> None:
        """Rows written before this schema may carry extra keys; ignore them."""
        response = _response(
            {"language_breakdown": [{"name": "Python", "percentage": 100.0, "x": 1}]}
        )

        assert response.language_breakdown == [
            jobs_schemas.LanguageShare(name="Python", percentage=100.0)
        ]


# ======================================================================
# 4. Both repository projections carry the columns
# ======================================================================
#
# The list and detail routes answer with the same schema. Projecting for the
# detail query alone would make the field real on one route and null on the other
# for the very same completed job.


def _model(**overrides: object) -> AnalysisJobModel:
    """A stand-in carrying every attribute either mapper reads.

    Typed as the ORM model so the mappers accept it directly. `SimpleNamespace`
    would work at runtime and fail mypy, which is the right way round: the
    mappers only read attributes, so nothing here depends on ORM behaviour.
    """
    fields: dict[str, object] = {
        "id": uuid4(),
        "repo_id": uuid4(),
        "workspace_id": uuid4(),
        "triggered_by": uuid4(),
        "trigger_type": "manual",
        "repo_url": "local:///repo",
        "branch": "main",
        "deep_scan": False,
        "depth": 1,
        "simulate_users": 0,
        "status": "completed",
        "progress_pct": 100,
        "progress_message": "Analysis complete",
        "total_files": 12,
        "total_lines": 900,
        "total_findings": 3,
        "critical_count": 0,
        "high_count": 1,
        "medium_count": 2,
        "low_count": 0,
        "overall_score": 80,
        "performance_score": 80,
        "security_score": 75,
        "reliability_score": 85,
        "maintainability_score": 80,
        "devops_score": 80,
        "blocked_by": [],
        "engine_statuses": {},
        "error_message": None,
        "started_at": None,
        "completed_at": None,
        "duration_seconds": 42,
        "created_at": None,
        "languages_detected": ["Python", "Go"],
        "language_breakdown": [
            {"name": "Python", "percentage": 80.0},
            {"name": "Go", "percentage": 20.0},
        ],
    }
    fields.update(overrides)
    return cast(AnalysisJobModel, SimpleNamespace(**fields))


class TestBothProjectionsCarryTheColumns:
    def test_the_list_mapping_includes_both_columns(self) -> None:
        row = JobRepository._to_dict_list(_model())

        assert row["languages_detected"] == ["Python", "Go"]
        assert row["language_breakdown"] == [
            {"name": "Python", "percentage": 80.0},
            {"name": "Go", "percentage": 20.0},
        ]

    def test_the_detail_mapping_includes_both_columns(self) -> None:
        row = JobRepository._to_dict(_model())

        assert row["languages_detected"] == ["Python", "Go"]
        assert row["language_breakdown"] == [
            {"name": "Python", "percentage": 80.0},
            {"name": "Go", "percentage": 20.0},
        ]

    def test_both_mappings_agree_on_the_columns(self) -> None:
        """A field present on one route and absent on the other is the bug."""
        detail = set(JobRepository._to_dict(_model()))
        listing = set(JobRepository._to_dict_list(_model()))

        assert {"languages_detected", "language_breakdown"} <= listing
        assert {"languages_detected", "language_breakdown"} <= detail

    def test_an_unwritten_row_maps_to_none_rather_than_a_list(self) -> None:
        """Jobs that predate these writes must not gain an empty mix."""
        model = _model(languages_detected=None, language_breakdown=None)

        row = JobRepository._to_dict(model)

        assert row["languages_detected"] is None
        assert row["language_breakdown"] is None

    def test_the_list_projection_selects_the_columns(self) -> None:
        """`_list_load_only` must ask for them, or the mapper reads unloaded
        attributes and every list request raises."""
        import inspect
        import re

        source = inspect.getsource(JobRepository._list_load_only)
        projected = set(re.findall(r"AnalysisJobModel\.(\w+)", source))

        assert "languages_detected" in projected
        assert "language_breakdown" in projected
