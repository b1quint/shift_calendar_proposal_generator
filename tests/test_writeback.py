"""Step-5 tests for output/writeback — the CSV export.

Pure row-shaping is asserted directly; the file write is exercised against a
tmp_path. We check the header (base + stable term columns), that unfilled rows
leave person/score/terms blank, the 4-dp numeric formatting, and that an actual
file is produced and round-trips through csv.
"""

import csv
from datetime import date, timedelta

from shift_proposer.models import Assignment, Block, Person, Proposal, Rationale
from shift_proposer.output.writeback import to_csv_rows, write_csv

ANN = Person("Ann")
MON = date(2026, 6, 1)


def block(start: date, n: int = 4) -> Block:
    return Block(dates=tuple(start + timedelta(days=i) for i in range(n)))


def assignment(person: Person, start: date) -> Assignment:
    rationale = Rationale(
        total=3.42,
        terms={"total": 2.67, "weekend": 0.5, "spacing": 0.0, "question": -0.5},
    )
    return Assignment(person=person, block=block(start), rationale=rationale)


def test_header_is_base_columns_plus_ordered_terms():
    rows = to_csv_rows(Proposal(assignments=(assignment(ANN, MON),)))
    assert rows[0] == [
        "status",
        "start",
        "end",
        "person",
        "score",
        "total",
        "weekend",
        "spacing",
        "question",
    ]


def test_proposed_row_formats_dates_and_numbers():
    rows = to_csv_rows(Proposal(assignments=(assignment(ANN, MON),)))
    assert rows[1] == [
        "proposed",
        "2026-06-01",
        "2026-06-04",
        "Ann",
        "3.4200",
        "2.6700",
        "0.5000",
        "0.0000",
        "-0.5000",
    ]


def test_unfilled_row_leaves_person_score_and_terms_blank():
    proposal = Proposal(
        assignments=(assignment(ANN, MON),), unfilled=(block(MON + timedelta(days=7)),)
    )
    rows = to_csv_rows(proposal)
    unfilled = rows[2]
    assert unfilled[:5] == ["unfilled", "2026-06-08", "2026-06-11", "", ""]
    assert unfilled[5:] == ["", "", "", ""]  # all term columns blank


def test_write_csv_creates_a_file_that_round_trips(tmp_path):
    proposal = Proposal(assignments=(assignment(ANN, MON),))
    out = write_csv(proposal, tmp_path / "proposal.csv")
    assert out.exists()
    with out.open(newline="", encoding="utf-8") as handle:
        read_back = list(csv.reader(handle))
    assert read_back == to_csv_rows(proposal)
