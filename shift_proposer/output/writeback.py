"""Persist a :class:`Proposal` — for review, never into live rows.

v1 target is a **CSV** (``Settings.output_target`` will later select the
gspread "proposed column" path; deferred until the first live run). A CSV is the
safest possible writeback: it cannot touch the spreadsheet's live assignment
rows, and it is fully testable without auth.

Row shaping is reused from :mod:`output.proposal` so the CSV columns line up with
the review report. Each row carries the per-term score breakdown, so the *why*
behind every pick is exported alongside the pick.
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path

from shift_proposer.models import Proposal
from shift_proposer.output.proposal import term_columns, to_rows

_BASE_HEADER = ("status", "start", "end", "person", "score")


def _num(value: float | None) -> str:
    """Format a numeric cell to 4 dp; blank for ``None`` (unfilled rows)."""
    return "" if value is None else f"{value:.4f}"


def to_csv_rows(proposal: Proposal) -> list[list[str]]:
    """The CSV as a list of string rows, header first.

    Pure (no filesystem) so the exact output is unit-testable. Score-term columns
    are appended after the base columns, in the stable preferred order.
    """
    rows = to_rows(proposal)
    terms = term_columns(rows)
    header = [*_BASE_HEADER, *terms]

    out: list[list[str]] = [header]
    for row in rows:
        out.append(
            [
                row.status,
                row.start.isoformat(),
                row.end.isoformat(),
                row.person,
                _num(row.score),
                *(_num(row.terms.get(term)) for term in terms),
            ]
        )
    return out


def _write_rows(rows: Sequence[Sequence[str]], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(rows)


def write_csv(proposal: Proposal, path: str | Path) -> Path:
    """Write ``proposal`` to a CSV at ``path``; return the path written."""
    target = Path(path)
    _write_rows(to_csv_rows(proposal), target)
    return target
