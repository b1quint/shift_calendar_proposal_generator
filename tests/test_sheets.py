"""Step-4 tests for io/sheets — the gspread adapter, without the network.

We never hit OAuth or Google here: fakes stand in for the gspread client /
spreadsheet / worksheet. We assert that cells are stringified, that the
unformatted render option is requested (so dates arrive as serials), that the
spreadsheet id / tab name are threaded through, and that a missing id is a clear
error. Live auth (``authorize``) is intentionally untested.
"""

import pytest
from gspread.utils import ValueRenderOption

from shift_proposer.config import Settings
from shift_proposer.io.sheets import (
    fetch_grid,
    open_worksheet,
    read_raw_grid,
)


class FakeWorksheet:
    def __init__(self, values):
        self._values = values
        self.last_kwargs = None

    def get_all_values(self, **kwargs):
        self.last_kwargs = kwargs
        return self._values


class FakeSpreadsheet:
    def __init__(self, worksheet):
        self._worksheet = worksheet
        self.requested_tab = None

    def worksheet(self, name):
        self.requested_tab = name
        return self._worksheet


class FakeClient:
    def __init__(self, spreadsheet):
        self._spreadsheet = spreadsheet
        self.opened_key = None

    def open_by_key(self, key):
        self.opened_key = key
        return self._spreadsheet


def test_fetch_grid_stringifies_cells_and_requests_unformatted():
    # Mixed types as gspread returns under UNFORMATTED_VALUE: serial ints, text,
    # empty cells.
    ws = FakeWorksheet([[46184, "AS", ""], ["Ann", None, "X"]])
    grid = fetch_grid(ws)
    assert grid == [["46184", "AS", ""], ["Ann", "", "X"]]
    assert ws.last_kwargs == {"value_render_option": ValueRenderOption.unformatted}


def test_open_worksheet_requires_a_sheet_id():
    with pytest.raises(ValueError, match="sheet_id is required"):
        open_worksheet(client=None, settings=Settings(sheet_id=None))


def test_open_worksheet_threads_id_and_tab_name():
    ws = FakeWorksheet([])
    spreadsheet = FakeSpreadsheet(ws)
    client = FakeClient(spreadsheet)
    settings = Settings(sheet_id="SHEET123", tab_name="SupSci")

    result = open_worksheet(client, settings)

    assert result is ws
    assert client.opened_key == "SHEET123"
    assert spreadsheet.requested_tab == "SupSci"


def test_read_raw_grid_uses_injected_client_end_to_end():
    ws = FakeWorksheet([[46184, "A"]])
    client = FakeClient(FakeSpreadsheet(ws))
    settings = Settings(sheet_id="SHEET123")

    grid = read_raw_grid(settings, client=client)

    assert grid == [["46184", "A"]]
