# Reseller Revenue Monitor: SQL → Growth Engine → Narrative → Agent

A small, fully reproducible pipeline for a Meesho-style reseller business. It computes real
revenue numbers with SQL, turns "significant change" into an explicit 8% rule, writes
stakeholder narratives from those verified numbers, and runs a mock monitoring agent that
drafts messages and holds them for human approval.

Everything is plain Python (standard library) plus SQLite. **No API keys, no network, no
message sending.**

---

## Quick start

```bash
pip install -r requirements.txt   # only openpyxl, used for the Part 2 spreadsheet
./run_all.sh                      # regenerates the dataset and runs every Part in order
```

`run_all.sh` stops at the first failure. A successful run ends with `== Done. All tests passed.`
(30 tests: 9 + 5 + 16).

Requirements: Python 3.9 or newer (tested on 3.12). `PYTHON=python ./run_all.sh` overrides the
interpreter name.

## Repository layout

```
generate_data.py          Part 1 data generator (seed 42 → resellers.csv, orders.csv, meesho_reseller.db)
run_all.sh                one command: regenerate + run every Part
part1_sql/                the five SQL queries (queries/*.sql), run_queries.py, output/*.csv
part2_engine/             growth_engine.py, tests, fixtures/, build_report.py → growth_report.xlsx
part3_narrative/          prompt_pack.md, narrative_report.md, masking.py, template_fill.py, tests
part4_agent/              agent_spec.md, mock_agent_runner.py, tests, data/, fixtures/, output/*.json
```

## 1. Regenerate the dataset

The dataset is synthetic and deterministic (`random.Random(42)`), so regenerating gives
byte-identical files.

```bash
python generate_data.py                      # writes resellers.csv, orders.csv, meesho_reseller.db
cp meesho_reseller.db part1_sql/             # the SQL queries run against this copy
```

Result: 24 resellers (6 per region), 900 orders (300 each for April, May and June), and one
reseller (`RS024`) with zero orders on purpose, to test the `LEFT JOIN` case.

## 2. Run every Part in order

Run from the repository root unless a `cd` is shown.

**Part 1: SQL** (`part1_sql/`)

```bash
cd part1_sql && python run_queries.py && cd ..
```

Runs the five queries and saves one CSV each in `part1_sql/output/`:
`monthly_category_revenue.csv`, `region_revenue.csv`, `top_resellers.csv`,
`zero_order_resellers.csv` (plus `count_star_vs_count_col.csv`, which shows why `COUNT(*)`
returns 1 for `RS024` while `COUNT(order_id)` returns 0) and `june_delivered_aov.csv`.
The `.sql` files are in `part1_sql/queries/`.

**Part 2: growth engine** (`part2_engine/`)

```bash
cp part1_sql/output/monthly_category_revenue.csv part2_engine/fixtures/
cd part2_engine
python -m unittest -v test_growth_engine     # 9 Given-When-Then tests
python build_report.py                        # growth_report.xlsx, flagged rates highlighted
cd ..
```

`growth_engine.py` provides `mom_growth`, `is_flagged` (returns `flagged`, `not_flagged` or
`escalate_exact_boundary`, never a bare boolean) and `validate_feed`. The spreadsheet uses
formulas, so it calculates when opened in Excel or LibreOffice.

**Part 3: narrative** (`part3_narrative/`)

```bash
cd part3_narrative && python -m unittest -v test_masking && cd ..    # 5 tests
```

`prompt_pack.md` (trigger, inputs, prompt, checklist) and `narrative_report.md` (worked
narratives, chart-choice justification, masked top-reseller narrative) are documents to read.
`masking.py` has `alias_for` and `assert_no_raw_names_leak`; the test confirms the final
narrative leaks no raw reseller name. `template_fill.py` fills the prompt pack's template for
Part 4.

**Part 4: agent** (`part4_agent/`)

```bash
cd part4_agent
python make_feeds.py                          # splits Part 1's output into data/april|may|june.csv
python -m unittest -v test_mock_agent_runner  # 16 agent-level specs
python mock_agent_runner.py --month May  --previous data/april.csv --current data/may.csv
python mock_agent_runner.py --month June --previous data/may.csv   --current data/june.csv
cd ..
```

Each run prints one JSON object (schema in `part4_agent/agent_spec.md`). Saved examples are in
`part4_agent/output/`, including a Hard Stop on the corrupted feed (exit code 1, expected) and
the synthetic exact-boundary case. In the May run, 3 flagged categories are drafted and 2 are
suppressed by the cap; drafts are **held for human approval**, never sent.

## 3. Runs with zero API keys

The whole pipeline runs with no API keys set:

- I ran `run_all.sh` from scratch with an **empty environment** (`env -i`, so no
  `ANTHROPIC_API_KEY` or any other variable) in a sandbox with **no network access**. All 30
  tests passed, and every generated file (dataset, CSVs, JSON) was byte-identical to the
  committed copy.
- No file imports an HTTP, socket, mail or LLM library. `test_mock_agent_runner.py` also checks
  that the runner source contains no network or mail code.
- The "drafting" step is deterministic template filling (`part3_narrative/template_fill.py`),
  not a model call. It follows the prompt pack's rules, and the runner raises an error if a
  draft contains any number that is not a supplied Part 1 / Part 2 value.

## 4. How each Part maps to its workflow pattern

| Part | Pattern it implements |
|---|---|
| **Part 1: SQL** | **Compute real numbers first.** Every figure comes from a deterministic query on the data, so no later step does its own arithmetic or guesses a number. |
| **Part 1 → Part 2** | **Compute with SQL, then hand off.** `monthly_category_revenue.csv` is the exact input contract (`month,category,revenue,n_orders`) the engine and agent consume. |
| **Part 2: growth engine** | **Make the rule explicit, then guard it.** "Significant change" becomes an 8% threshold with a three-way outcome, so the exact boundary goes to a human instead of being auto-decided. `validate_feed` is the input guardrail. |
| **Part 3: narrative** | **Constrained prompting with a validation checklist.** The prompt pack fixes the inputs and a Context → Insight → Implication structure, labels every claim as fact, hypothesis or action, and checks the output. `masking.py` enforces the privacy policy. |
| **Part 4: agent** | **Intake → Summary → Report Draft → Validate.** *Intake*: load and validate both feeds (Hard Stop if invalid). *Summary*: compute MoM, flag, rank. *Report Draft*: draft the top 3 via the Part 3 template, suppress the rest, log boundary cases. *Validate*: trace every number, then hold for human approval and emit the JSON object. |
| **Part 2 + 3 → Part 4** | **Reuse, don't rebuild.** The agent imports `growth_engine` unmodified and fills the same prompt pack, so tested logic runs unchanged inside the larger workflow. |

## Notes and assumptions

- Revenue in Parts 1 to 4 is `SUM(quantity * unit_price)` over **all order statuses**
  (delivered, returned, cancelled and pending), as the brief specified. The narratives call
  this out and recommend a delivered-only cut before decisions are made.
- With an 8% threshold, nearly every category-month in this synthetic data is flagged
  (9 of 10 in `growth_report.xlsx`), which is why Part 4 caps drafts at 3 per run.
- Case matching in `assert_no_raw_names_leak` is exact and case-sensitive, as specified.
