# Handoff / build progress

Building the Shift Calendar Proposal Generator (see [CLAUDE.md](CLAUDE.md)) from scratch,
following its suggested build order.

- **Branch:** `mvp-v1` (not pushed)
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

53 tests passing, ruff clean.

## Decisions locked this build (beyond CLAUDE.md)

- Count unit = **shift-days**.
- Fair share = **equal split** (`total / N`).
- `quarter_seed` = **carry_deviation**.
- blocks: short remainders (< `shift_len`) **silently dropped** — OK'd for review; revisit if
  remainders should be *flagged* instead.

## Next — step 4 (test-first, stop for review after each module)

1. **`io/parser.py`** — raw cell grid → `AvailabilityGrid` + existing assignments
   (`Mapping[Person, list[date]]`, the shape `greedy.propose(existing=...)` expects). Maps
   `A/AS/AR/-` → available via `Code.parse`. Testable with fixture grids (no Sheets).
2. **`io/sheets.py`** — gspread + OAuth adapter: SupSci tab ↔ raw cell grid. The ONLY gspread
   import. Not unit-tested against the network.

Then **step 5** (`output/proposal.py`, `output/writeback.py`), **step 6** (`cli.py` wiring).

## Commits

- `c892529` — engine/greedy: date-ordered greedy fill into a Proposal
- `c2a5b2d` — engine/scoring: weighted candidate score with per-term rationale
- `c323e79` — engine/eligibility: hard candidate gate (X-block + min rest)
- `a7ba08f` — engine/blocks: enumerate unfilled shift-length blocks
- `fbb90ad` — engine/tallies: two-horizon fairness counters
- `eaa911f` — scaffold: domain models, Settings, uv tooling
