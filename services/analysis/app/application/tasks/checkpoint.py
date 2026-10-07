"""The pipeline's saved position, so a failed run can resume where it stopped.

After every stage the orchestrator writes its in-memory state -- the parsed
files, the rule violations, each finished engine's results, the score -- to a
file keyed by the job's own id. A retry of a failed job reads that file back
and starts at the stage that failed instead of at clone, so the percentage a
run reached is the percentage it continues from and nothing already finished
runs twice.

Design notes:

- The file lives in the same ephemeral directory as the cloned workspace, and
  the path is derived from the job's UUID -- never from anything a caller
  supplies. The data is this service's own pipeline state; nothing
  user-controlled is ever unpickled.
- Pickle, not JSON: the state is domain objects (parsed files, engine result
  dataclasses, findings) that JSON cannot carry.
- Writes are best-effort and atomic (write to a temp file, then rename): a
  full disk or a torn write must never fail the analysis itself. The cost of
  losing a checkpoint is only that the next retry starts from the beginning
  rather than resuming.
- The file is deleted when a run completes, and when the job is deleted. A
  failed run keeps its checkpoint -- that file is the resume point.
"""

import contextlib
import os
import pickle
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import cast
from uuid import UUID

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# `time.monotonic()` values are meaningless across process boundaries: the
# marker records when *this* process started its clock, and a resumed run must
# re-measure. It is rebuilt by `_run_pipeline` on every entry, so carrying it
# over would only be stale data waiting to be trusted.
_EXCLUDED_KEYS = ("_pipeline_start",)


def _checkpoint_dir() -> Path:
    return Path(get_settings().analysis.ephemeral_path)


def _checkpoint_path(job_id: UUID) -> Path:
    return _checkpoint_dir() / f"{job_id.hex}.state"


def save_checkpoint(job_id: UUID, state: Mapping[str, object]) -> None:
    """Persist the pipeline state after a completed stage.

    Raises on failure: callers are expected to treat this as best-effort and
    log, because losing a checkpoint costs a future resume, not this run.
    """
    snapshot = {k: v for k, v in state.items() if k not in _EXCLUDED_KEYS}
    path = _checkpoint_path(job_id)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write-then-rename, so a reader never sees a half-written file: a retry
    # arriving mid-save would otherwise unpickle garbage and refuse to resume
    # a run whose position was perfectly fine one millisecond earlier.
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            pickle.dump(snapshot, fh, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp_name, path)
    except BaseException:
        # The temp file never became the real one, so a reader cannot meet it;
        # removing it here only keeps the directory free of debris.
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


def load_checkpoint(job_id: UUID) -> dict[str, object] | None:
    """The saved state for a job, or None when there is nothing usable.

    None covers every way the file can be absent or wrong: never written (the
    job failed before its first stage finished), deleted with the container's
    /tmp, written by a version of the state shape this code no longer reads,
    or truncated by a disk full mid-write. All of them mean the same thing to
    the caller: this run cannot resume.
    """
    path = _checkpoint_path(job_id)
    try:
        with path.open("rb") as fh:
            raw: object = pickle.load(fh)
    except FileNotFoundError:
        return None
    except Exception:
        logger.warning("checkpoint_unreadable", job_id=str(job_id))
        return None
    if not isinstance(raw, dict):
        logger.warning("checkpoint_not_a_mapping", job_id=str(job_id))
        return None
    return cast(dict[str, object], raw)


def delete_checkpoint(job_id: UUID) -> None:
    """Drop a job's saved position. Best-effort: an orphaned file costs only
    a few megabytes of ephemeral disk, and /tmp outlives neither the
    container nor this service's attention."""
    try:
        _checkpoint_path(job_id).unlink(missing_ok=True)
    except OSError as exc:
        logger.warning("checkpoint_delete_failed", job_id=str(job_id), error=str(exc))
