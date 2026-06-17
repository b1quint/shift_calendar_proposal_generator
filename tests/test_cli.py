"""Step-6 tests for cli — the wiring, exercised without the network.

A fake gspread client (reused shape from test_sheets) feeds a hand-built SupSci
grid through the whole pipeline: sheets -> parser -> engine -> Proposal. We also
assert window selection (pure) and argument parsing. Live OAuth in ``main`` is
not tested.
"""

from datetime import date

from shift_proposer.cli import (
    parse_args,
    propose_from_sheet,
    select_window,
)
from shift_proposer.config import Settings
from shift_proposer.models import AvailabilityGrid, Person

ANN = Person("Ann")
BO = Person("Bo")


# --- fakes (no network) ----------------------------------------------------


class FakeWorksheet:
    def __init__(self, values):
        self._values = values

    def get_all_values(self, **kwargs):
        return self._values


class FakeSpreadsheet:
    def __init__(self, worksheet):
        self._worksheet = worksheet

    def worksheet(self, name):
        return self._worksheet


class FakeClient:
    def __init__(self, values):
        self._spreadsheet = FakeSpreadsheet(FakeWorksheet(values))

    def open_by_key(self, key):
        return self._spreadsheet


# A minimal SupSci grid: 4 consecutive available dates, two people, no prior
# assignments -> exactly one 4-day block.
SHEET = [
    ["", "", "", "", "", "", ""],  # row 1: month header
    ["", "", "", "2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04"],  # row 2: dates
    ["", "", "", "", "", "", ""],  # row 3: weekday
    ["", "", "", "", "", "", ""],  # row 4: avail count
    ["", "", "", "", "", "", ""],  # row 5: shift summary
    ["Ann", "AB", "avail", "", "", "", ""],  # row 6: Ann availability (all available)
    ["", "", "shift", "", "", "", ""],  # row 7: Ann shift (none)
    ["Bo", "BC", "avail", "", "", "", ""],  # row 8: Bo availability
    ["", "", "shift", "", "", "", ""],  # row 9: Bo shift (none)
    ["", "", "", "", "", "", ""],  # row 10: blank name -> end
]


# --- window selection (pure) -----------------------------------------------


def _grid(dates):
    return AvailabilityGrid(people=(ANN,), dates=tuple(dates), codes={})


def test_select_window_no_bounds_returns_grid_unchanged():
    grid = _grid([date(2026, 6, 1), date(2026, 6, 2)])
    assert select_window(grid, None, None) is grid


def test_select_window_filters_to_bounds_inclusive():
    days = [date(2026, 6, d) for d in (1, 2, 3, 4, 5)]
    grid = _grid(days)
    narrowed = select_window(grid, date(2026, 6, 2), date(2026, 6, 4))
    assert narrowed.dates == (date(2026, 6, 2), date(2026, 6, 3), date(2026, 6, 4))


# --- full pipeline through a fake sheet ------------------------------------


def test_propose_from_sheet_runs_end_to_end():
    settings = Settings(sheet_id="SHEET123")
    proposal = propose_from_sheet(settings, client=FakeClient(SHEET))
    # One block; tie between two never-assigned people resolves to lowest name.
    assert len(proposal.assignments) == 1
    assert proposal.assignments[0].person == ANN
    assert proposal.assignments[0].block.dates[0] == date(2026, 6, 1)
    assert proposal.unfilled == ()


def test_propose_from_sheet_honors_the_window():
    # Window keeps only 3 of the 4 dates -> no full 4-day block -> nothing to do.
    settings = Settings(
        sheet_id="SHEET123",
        window_start=date(2026, 6, 1),
        window_end=date(2026, 6, 3),
    )
    proposal = propose_from_sheet(settings, client=FakeClient(SHEET))
    assert proposal.assignments == ()
    assert proposal.unfilled == ()


# --- argument parsing ------------------------------------------------------


def test_parse_args_defaults():
    args = parse_args([])
    assert args.csv.name == "proposal.csv"
    assert args.sheet_id is None
    assert args.window_start is None


def test_parse_args_reads_window_and_sheet_id():
    args = parse_args(
        ["--sheet-id", "XYZ", "--window-start", "2026-06-01", "--window-end", "2026-06-30"]
    )
    assert args.sheet_id == "XYZ"
    assert args.window_start == date(2026, 6, 1)
    assert args.window_end == date(2026, 6, 30)
