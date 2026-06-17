# Handoff / build progress

Building the Shift Calendar Proposal Generator (see [CLAUDE.md](CLAUDE.md)) from scratch,
following its suggested build order.

- **Branch:** `mvp-v1` (pushed, tracks `origin/mvp-v1`)
- **Package manager:** `uv` (installed via Homebrew)
- **Run tests:** `uv run pytest -q`
- **Lint / format:** `uv run ruff check .` / `uv run ruff format .`

## Done (committed on `mvp-v1`)

- **Step 1 — scaffold:** flat `shift_proposer/` package, `models.py` (pure domain types),
  `config.py` (`Settings` + `from_env` for `SHIFT_SHEET_ID`), `.gitignore` for secrets, uv tooling.
- **Step 2 — `engine/tallies.py`:** two-horizon fairness counters. Stores assigned dates per
  person; derives YTD + calendar-quarter by filtering. `total_deficit` / `weekend_deficit`
  (positive = below fair share). Quarter seeded via `carry_deviation` (one-line switch to
  `carry_total` / `zero`).
- **Step 3a — `engine/blocks.py`:** `enumerate_blocks(dates, filled, shift_len)` → full
  `shift_len`-day blocks over consecutive unfilled calendar days, date order. Short tails dropped.
- **Step 3b — `engine/eligibility.py`:** hard candidate gate. `is_available_for_block` (reject any
  `X`; `?` stays eligible), `is_rested_for_block` (`min_rest_rotations * shift_len` days since last
  shift; never-assigned ⇒ rested), `is_eligible`, `eligible_people` (grid-ordered pool). "Skip
  filled" is handled upstream by `blocks.py`.
- **Step 3c — `engine/scoring.py`:** `score(grid, tallies, settings, person, block) -> (float,
  Rationale)`. Weighted sum: `+w_total*total_deficit +w_weekend*weekend_deficit
  +w_spacing*days_since_last -w_question*n_question`. `Rationale.terms` hold the *weighted*
  contributions (sum to total). Never-assigned ⇒ spacing term `0` (tunable choice).
- **Step 3d — `engine/greedy.py`:** `propose(grid, settings, existing=None) -> Proposal`. Seeds
  tallies + filled dates from `existing`, enumerates blocks, per block: eligible → score → pick
  highest (stable tie-break: lowest YTD load, then name) → record. Empty pool ⇒ block flagged
  unfilled. **The pure engine (step 3) is complete.**
- **Step 4a — `io/parser.py`:** raw cell grid → `AvailabilityGrid` + existing assignments
  (`dict[Person, list[date]]`). Encodes the real SupSci layout in a configurable `LayoutConfig`
  (names col A from row 6, calendar col D from row 2, 2 rows/person). `A/AS/AR/-` collapse via
  `Code.parse`; `?`/`X` preserved; assignments read from each person's shift row. `parse_date_row`
  resolves ISO or Sheets serials; bare day-of-month rejected as ambiguous (pass `dates=` to
  override).
- **Step 4b — `io/sheets.py`:** gspread + OAuth adapter (the ONLY gspread import). Fetches
  `UNFORMATTED_VALUE` (dates → serials), stringifies cells. `read_raw_grid` validates `sheet_id`
  before authorizing (fail fast). `load_sheet` = read + parse. Wiring tested with fakes; live
  `authorize()` untested.
- **Step 5a — `output/proposal.py`:** pure render layer. `to_rows` (chronological `ProposalRow`,
  unfilled merged inline) + `render_report` (text, score trace inline, unfilled flagged) +
  `term_columns`.
- **Step 5b — `output/writeback.py`:** CSV export (`to_csv_rows` pure, `write_csv` writes). Columns
  match the report (base + stable term columns); 4-dp numbers; never live rows. Proposed-column
  path deferred to first live run.
- **Step 6 — `cli.py`:** `Settings.from_env → load_sheet → select_window → propose → render_report
  + write_csv`. `[project.scripts]` entrypoint `shift-proposer`. Flags: `--csv`, `--sheet-id`,
  `--tab`, `--window-start/-end`. Pipeline tested through a fake sheet; only `main()` touches OAuth.

**84 tests passing, ruff clean. All six build steps complete — MVP is functionally done.**

## Decisions locked this build (beyond CLAUDE.md)

- Count unit = **shift-days**.
- Fair share = **equal split** (`total / N`).
- `quarter_seed` = **carry_deviation**.
- blocks: short remainders (< `shift_len`) **silently dropped** — OK'd for review; revisit if
  remainders should be *flagged* instead.

## Next — first live run + follow-ups

1. **First end-to-end run** against the real sheet (needs `SHIFT_SHEET_ID` + one-time OAuth):
   - One-time auth: place OAuth client secrets at `~/.config/gspread/credentials.json`, then
     `SHIFT_SHEET_ID=<id> uv run shift-proposer --window-start … --window-end …`.
   - **Verify the date encoding**: if row 2 is a bare day-of-month, the parser raises "ambiguous";
     that's the signal to resolve dates from the sheet's year (or confirm `UNFORMATTED_VALUE`
     returns true serials).
2. **`output/writeback.py` proposed-column path** — write back into a separate proposed column on
   the sheet (`output_target = "proposed_column"`), designed once we've seen the live layout.
3. **Tune weights** in `Settings` against real numbers; revisit `quarter_seed` and whether short
   block remainders should be *flagged* rather than dropped.

## Commits

- `62ee494` — cli: wire Settings -> sheets -> engine -> output (step 6)
- `a07da3b` — output/writeback: CSV export of a Proposal
- `6c92911` — output/proposal: render Proposal as review report + rows
- `182e2a4` — io/sheets: gspread+OAuth adapter -> raw SupSci grid
- `46e4256` — io/parser: raw SupSci grid -> AvailabilityGrid + existing assignments
- `c892529` — engine/greedy: date-ordered greedy fill into a Proposal
- `c2a5b2d` — engine/scoring: weighted candidate score with per-term rationale
- `c323e79` — engine/eligibility: hard candidate gate (X-block + min rest)
- `a7ba08f` — engine/blocks: enumerate unfilled shift-length blocks
- `fbb90ad` — engine/tallies: two-horizon fairness counters
- `eaa911f` — scaffold: domain models, Settings, uv tooling
