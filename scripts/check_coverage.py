#!/usr/bin/env python
"""Fail CI if a coverage report is missing, thin, or vacuous.

``fail_under`` in a service's pyproject.toml is enforced by pytest-cov, and it
is a good gate. It has one blind spot, though, and this check closes it.

A percentage of zero statements is 100%. ``services/notifications`` declares
``fail_under = 90`` and passes it, because every module under ``app/`` is a
0-byte file: there is nothing to execute, so coverage measures nothing and
reports total success. The same thing happens the moment real code is moved,
renamed out of the measured paths, or excluded by a pattern -- the floor stays
green while the tests it was supposed to vouch for stop running.

So this checks three things, not one:

1. ``coverage.xml`` exists. No report means no measurement, which is not a pass.
2. The report measured a real body of code. A floor is only meaningful against
   a non-trivial statement count, so anything under ``MIN_STATEMENTS`` fails
   regardless of the percentage it reports.
3. The measured rate meets the declared floor. Duplicated from pytest-cov on
   purpose: the number in the job summary and the number that gates the build
   come from the same place, and the summary cannot quietly disagree with it.

Run directly from a service directory:

    python ../../scripts/check_coverage.py
"""

from __future__ import annotations

import os
import sys
import tomllib
import xml.etree.ElementTree as ET

# Below this, a percentage is not evidence of anything. Set well under the
# smallest real service in the repo so it only fires on an empty or gutted
# package, never on a small one.
MIN_LINES = 500

REPORT = "coverage.xml"
PYPROJECT = "pyproject.toml"


def fail(message: str) -> int:
    print(f"coverage check FAILED: {message}", file=sys.stderr)
    return 1


def main() -> int:
    service = os.path.basename(os.getcwd())

    if not os.path.exists(REPORT):
        return fail(
            f"{service}: no {REPORT}. The tests ran but nothing was measured, "
            f"which is not a pass."
        )

    try:
        root = ET.parse(REPORT).getroot()
    except ET.ParseError as exc:
        return fail(f"{service}: {REPORT} is not valid XML ({exc}).")

    # Cobertura as coverage.py actually writes it. The root carries the
    # totals; <class> elements carry only filename/name/rates, with the
    # per-line detail nested as <line> children. There is no num_statements
    # attribute anywhere, which is worth stating because an earlier version of
    # this script read one and reported 0 statements for every real report.
    measurable = int(root.attrib.get("lines-valid", 0))
    covered = int(root.attrib.get("lines-covered", 0))

    if measurable < MIN_LINES:
        return fail(
            f"{service}: only {measurable} measurable lines, below the "
            f"{MIN_LINES} minimum. A percentage over almost no code is not "
            f"evidence -- check that the package still has real modules and "
            f"that they are not excluded from measurement."
        )

    if not os.path.exists(PYPROJECT):
        return fail(f"{service}: no {PYPROJECT}, so no floor to check against.")

    with open(PYPROJECT, "rb") as fh:
        config = tomllib.load(fh)

    try:
        floor = config["tool"]["coverage"]["report"]["fail_under"]
    except KeyError:
        return fail(
            f"{service}: no [tool.coverage.report] fail_under declared. "
            f"Without a floor this check has nothing to enforce."
        )

    # coverage.py's own percentage folds branches into the denominator:
    #   (covered_lines + covered_branches) / (statements + branches)
    # Counting lines alone gives a *higher* number -- 31.16% against 27.48% on
    # services/ai -- so a lines-only gate would be systematically more permissive
    # than the fail_under it shadows, which is the one thing a gate must not be.
    branches = int(root.attrib.get("branches-valid", 0))
    covered_branches = int(root.attrib.get("branches-covered", 0))

    numerator = covered + covered_branches
    denominator = measurable + branches
    rate = (numerator / denominator * 100) if denominator else 0.0

    if rate < floor:
        return fail(
            f"{service}: line coverage {rate:.2f}% is below the declared "
            f"floor of {floor}%."
        )

    detail = f"{covered}/{measurable} lines"
    if branches:
        detail += f", {covered_branches}/{branches} branches"
    print(f"{service}: coverage {rate:.2f}% (floor {floor}%, {detail})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
