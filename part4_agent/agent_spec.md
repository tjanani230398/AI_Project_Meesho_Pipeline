# Agent Specification: Category Revenue Monitor

A mock agent that watches month-on-month (MoM) revenue per category, flags large moves, and
**drafts** stakeholder updates that a human must approve. It is built only from this project's
own parts: Part 1 (data), Part 2 (`growth_engine.py`), Part 3 (prompt pack and
`template_fill.py`). Code: `mock_agent_runner.py`. Tests: `test_mock_agent_runner.py`.

---

## 4.1 The five components

**Goal.** Keep Meesho category managers informed of any category whose month-on-month revenue
moves beyond the 8% threshold, with a human approving every message before it goes out.

**Tools.** Concrete functions the agent calls, none of them re-implemented:

| Tool | From | Used for |
|---|---|---|
| `validate_feed(csv_path)` | Part 2 `growth_engine.py` | Input guardrail on both monthly feeds |
| `mom_growth(previous, current)` | Part 2 | MoM % per category |
| `is_flagged(mom_pct, threshold=8.0)` | Part 2 | `flagged` / `not_flagged` / `escalate_exact_boundary` |
| `build_inputs`, `fill_prompt`, `draft_message` | Part 3 `template_fill.py` | Fills the prompt pack's placeholders and produces the draft |
| `untraceable_numbers(text, inputs)` | Part 3 `template_fill.py` | Output guardrail on every draft |

`template_fill.py` is new in Part 3. It reads the prompt text straight from `prompt_pack.md`, so
the pack stays the single source of truth. Because no model call is allowed, `draft_message` is a
deterministic stand-in for the model's answer and follows the pack's rules.

**Memory / State.** Between runs the agent must remember each category's previous-month
revenue and order count, so the next run can compute MoM. This is held as the previous
month's validated feed (`previous_month_csv`, for example `data/april.csv`), which is the only
state the run needs. Each run's JSON object is also its log: what was drafted, suppressed
and escalated.

**Planner.** The ordered subtasks in section 4.2.

**Feedback loop.** A human-approval checkpoint sits between drafting and sending. Drafts are
never sent; the run ends with `action_taken = "drafted_and_held_for_approval"` and each draft
carries `drafted: true` plus its `message`. Approval is simulated by that held state: nothing
in the runner ever marks a message as sent, and there is no email, SMTP or network code.

### Guardrails

| Layer | Rule | Where enforced |
|---|---|---|
| **Input** | `validate_feed` must pass on both feeds before anything else runs. | Subtasks 1 and 2 |
| **Action** | No message is ever auto-sent, only drafted and held. At most 3 drafts per run. | Subtasks 6 and 8 |
| **Output** | Every number in a draft must trace back to a Part 1 / Part 2 value (revenue, order count, MoM %, threshold). A draft with any other number raises an error and is never emitted. | Subtask 6 |

Two extra input checks run after `validate_feed` passes, because the two feeds must also be
comparable. Any failure is a Hard Stop with a message in `validation_errors`: every row in the
current feed carries the `run_month`; the previous feed holds a single month; both feeds have
the same categories with no duplicates; `n_orders` is an integer; and no previous revenue is 0
(MoM would be undefined).

### Stopping conditions

- **Success:** drafts produced, or correctly zero drafts if nothing crossed the threshold, and
  every number in every draft is traceable. `validation_status = "valid"`.
- **Error:** `validate_feed` returns `False` on either feed (or a comparability check fails). The
  run is a **Hard Stop**: `validation_status = "invalid"`, `action_taken = "hard_stop"`, the
  errors are surfaced in `validation_errors`, nothing is drafted, and the runner exits non-zero.
  It is never a silent skip.

### Agent-level specs (the four Part 2 cases)

1. **GIVEN** April→May Ethnic Wear revenue moves from 104520.77 to 185107.61, **WHEN** the agent
   runs for May, **THEN** Ethnic Wear appears in `flagged_categories` with `mom_pct` 77.1 and a
   draft held for approval (it is the largest move, so it is drafted first).
2. **GIVEN** May→June Beauty & Personal Care revenue moves from 35542.11 to 37559.07, **WHEN** the
   agent runs for June, **THEN** its 5.67% growth is not flagged: the category appears in
   none of `flagged_categories`, `suppressed_categories` or `escalated_categories`.
3. **GIVEN** a synthetic pair `previous=100000, current=108000` (exactly on the threshold boundary),
   **WHEN** the agent runs, **THEN** the category is listed in `escalated_categories` and is not
   flagged, not suppressed and not drafted. It is held for human review.
4. **GIVEN** the corrupted feed fixture, **WHEN** the agent runs, **THEN** it Hard Stops with
   `validation_status = "invalid"`, `action_taken = "hard_stop"` and exactly 3 `validation_errors`,
   in order: the negative-revenue row, the missing-category row, the missing-revenue row.

Fixtures: specs 1 and 2 use `data/april.csv`, `data/may.csv`, `data/june.csv` (exact splits of
Part 1's `monthly_category_revenue.csv`); spec 3 uses `fixtures/boundary_prev.csv` and
`fixtures/boundary_curr.csv`; spec 4 uses Part 2's `fixtures/corrupted_feed.csv`.

---

## 4.2 Ordered subtasks (the Planner)

1. Load the monthly revenue feeds and run `validate_feed` on both.
2. If either is invalid, **Hard Stop** and report the errors.
3. If valid, compute `mom_growth` for every category against the previous month.
4. Run `is_flagged` on every category.
5. Sort flagged categories by `abs(mom_pct)` descending (ties broken by category name).
6. Draft a message (via Part 3's template) for **at most the top 3** by magnitude. The cap exists
   to prevent notification flooding: one message per flagged item with no limit.
7. Log any remaining flagged categories beyond the cap as `suppressed, review manually`, with no
   draft.
   **7b.** Separately, log any category whose `is_flagged` result is `"escalate_exact_boundary"`
   into `escalated_categories`, with no draft. An exact-boundary category is neither flagged nor
   not flagged, so it is never silently dropped from both lists or mistaken for either.
8. Emit one structured JSON object per run.

---

## 4.3 Structured JSON output

Every run, success or Hard Stop, emits one object with exactly these top-level keys:

| Key | Type | Meaning |
|---|---|---|
| `run_month` | string | Month being evaluated, as passed to `run()` |
| `validation_status` | `"valid"` / `"invalid"` | Result of the input guardrail |
| `validation_errors` | list of strings | Empty on success. Errors from the current feed are verbatim from `validate_feed`; errors from the previous feed carry the prefix `previous_month_csv: ` |
| `flagged_categories` | list of objects | Every flagged category, largest move first: `category`, `mom_pct`, `previous_revenue`, `current_revenue`, `drafted` (boolean), and `message` only if drafted |
| `suppressed_categories` | list of strings | Flagged categories beyond the cap of 3 (empty if none) |
| `escalated_categories` | list of strings | Categories at the exact boundary (empty unless one exists) |
| `action_taken` | `"drafted_and_held_for_approval"` / `"hard_stop"` | What the run did |

When a run succeeds with zero flagged categories, `action_taken` is still
`"drafted_and_held_for_approval"` (the hold applies to an empty set of drafts), because the
schema allows only these two values.

**Real scenario results** (full JSON in `output/`):

| Scenario | Flagged (drafted) | Suppressed | Escalated | `action_taken` |
|---|---|---|---|---|
| May (`may_run.json`) | Ethnic Wear +77.1, Western Wear -23.6, Kids Wear -23.48 | Beauty & Personal Care (-12.75), Home & Kitchen (-9.25) | none | `drafted_and_held_for_approval` |
| June (`june_run.json`) | Ethnic Wear -58.74, Home & Kitchen +42.59, Kids Wear +23.9 | Western Wear (+11.97) | none | `drafted_and_held_for_approval` |
| Corrupted feed (`hard_stop_run.json`) | none | none | none | `hard_stop` |
| Synthetic boundary (`boundary_run.json`) | Synthetic Flagged +20.0 | none | Synthetic Boundary | `drafted_and_held_for_approval` |

Beauty & Personal Care (+5.67) is not flagged in June, so it is in no list.

Hard Stop example (`hard_stop_run.json`):

```json
{
  "run_month": "July",
  "validation_status": "invalid",
  "validation_errors": [
    "line 3: negative revenue (-4200.00) for category=Western Wear",
    "line 4: missing category (month=July)",
    "line 6: missing revenue (category=Home & Kitchen)"
  ],
  "flagged_categories": [],
  "suppressed_categories": [],
  "escalated_categories": [],
  "action_taken": "hard_stop"
}
```

Run it yourself:

```bash
python mock_agent_runner.py --month May --previous data/april.csv --current data/may.csv
```
