"""Mock monitoring agent: validate -> compute -> flag -> rank -> draft (capped) -> log -> JSON.

Drafts are held for human approval; nothing is ever sent. No network, no API key.
Part 2's growth_engine functions are imported unmodified.
"""
import argparse
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _sub in ("part2_engine", "part3_narrative"):
    _p = os.path.join(ROOT, _sub)
    if _p not in sys.path:
        sys.path.insert(0, _p)

from growth_engine import ESCALATE, FLAGGED, is_flagged, mom_growth, validate_feed  # noqa: E402
from template_fill import build_inputs, draft_message, untraceable_numbers  # noqa: E402

THRESHOLD = 8.0
MAX_DRAFTS = 3  # notification-flooding cap


def _load_feed(path, role):
    """Read a feed already passed by validate_feed. Returns (data, months, errors)."""
    data, months, errors = {}, set(), []
    with open(path, newline="") as f:
        for line_no, row in enumerate(csv.DictReader(f), start=2):
            category = (row.get("category") or "").strip()
            months.add((row.get("month") or "").strip())
            if category in data:
                errors.append(f"{role}: line {line_no}: duplicate category {category!r}")
                continue
            raw_orders = (row.get("n_orders") or "").strip()
            try:
                n_orders = int(raw_orders)
            except ValueError:
                errors.append(f"{role}: line {line_no}: n_orders not an integer: {raw_orders!r}")
                continue
            data[category] = (float(row["revenue"]), n_orders)
    return data, months, errors


def _pairing_errors(month, prev, cur, prev_months, cur_months, load_errors):
    """Extra input guardrail: the two feeds must be comparable."""
    errors = list(load_errors)
    if cur_months != {month}:
        errors.append(f"current_month_csv: expected month {month!r} on every row, "
                      f"found {sorted(cur_months)}")
    if len(prev_months) != 1:
        errors.append(f"previous_month_csv: expected a single month, found {sorted(prev_months)}")
    if set(prev) != set(cur):
        errors.append(f"category sets differ: only in previous {sorted(set(prev) - set(cur))}; "
                      f"only in current {sorted(set(cur) - set(prev))}")
    for category, (revenue, _) in prev.items():
        if revenue == 0:
            errors.append(f"category {category!r}: previous revenue is 0, "
                          f"month-on-month growth undefined")
    return errors


def _result(month, status, errors, flagged, suppressed, escalated, action):
    return {
        "run_month": month,
        "validation_status": status,
        "validation_errors": errors,
        "flagged_categories": flagged,
        "suppressed_categories": suppressed,
        "escalated_categories": escalated,
        "action_taken": action,
    }


def _hard_stop(month, errors):
    return _result(month, "invalid", errors, [], [], [], "hard_stop")


def run(month: str, previous_month_csv: str, current_month_csv: str) -> dict:
    # (1) load the feeds and run validate_feed
    ok_cur, errs_cur = validate_feed(current_month_csv)
    ok_prev, errs_prev = validate_feed(previous_month_csv)
    # current-feed errors stay verbatim; previous-feed errors are prefixed
    errors = list(errs_cur) + [f"previous_month_csv: {e}" for e in errs_prev]

    # (2) invalid -> Hard Stop, errors surfaced
    if not (ok_cur and ok_prev):
        return _hard_stop(month, errors)

    prev, prev_months, load_prev = _load_feed(previous_month_csv, "previous_month_csv")
    cur, cur_months, load_cur = _load_feed(current_month_csv, "current_month_csv")
    errors = _pairing_errors(month, prev, cur, prev_months, cur_months, load_prev + load_cur)
    if errors:
        return _hard_stop(month, errors)
    prev_month = next(iter(prev_months))

    # (3) mom_growth and (4) is_flagged for every category
    flagged, escalated = [], []
    for category, (prev_rev, prev_orders) in prev.items():
        cur_rev, cur_orders = cur[category]
        growth = mom_growth(prev_rev, cur_rev)
        verdict = is_flagged(growth, THRESHOLD)
        row = (category, growth, prev_rev, cur_rev, prev_orders, cur_orders)
        if verdict == FLAGGED:
            flagged.append(row)
        elif verdict == ESCALATE:
            escalated.append(row)

    # (5) sort by abs(mom_pct) descending (ties: category name)
    def order(r):
        return (-abs(r[1]), r[0])
    flagged.sort(key=order)
    escalated.sort(key=order)

    # (6) draft at most the top MAX_DRAFTS; (7) log the rest as suppressed
    flagged_out, suppressed = [], []
    for rank, (category, growth, prev_rev, cur_rev, prev_o, cur_o) in enumerate(flagged):
        entry = {"category": category, "mom_pct": growth, "previous_revenue": prev_rev,
                 "current_revenue": cur_rev, "drafted": rank < MAX_DRAFTS}
        if entry["drafted"]:
            inputs = build_inputs(category, prev_month, month, prev_rev, cur_rev,
                                  growth, prev_o, cur_o, THRESHOLD)
            message = draft_message(inputs)
            stray = untraceable_numbers(message, inputs)  # output guardrail
            if stray:
                raise RuntimeError(f"untraceable numbers in draft for {category}: {stray}")
            entry["message"] = message
        else:
            suppressed.append(category)
        flagged_out.append(entry)

    # (7b) exact-boundary categories are logged, never drafted, never dropped
    escalated_out = [r[0] for r in escalated]

    # (8) one structured object per run; drafts are held, never sent
    return _result(month, "valid", [], flagged_out, suppressed, escalated_out,
                   "drafted_and_held_for_approval")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run the mock monitoring agent.")
    ap.add_argument("--month", required=True)
    ap.add_argument("--previous", required=True)
    ap.add_argument("--current", required=True)
    ap.add_argument("--out", help="also write the JSON to this path")
    args = ap.parse_args(argv)
    result = run(args.month, args.previous, args.current)
    text = json.dumps(result, indent=2, ensure_ascii=False)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    if result["action_taken"] == "drafted_and_held_for_approval":
        print("-- drafts are HELD for human approval; nothing was sent.", file=sys.stderr)
    return 0 if result["validation_status"] == "valid" else 1


if __name__ == "__main__":
    sys.exit(main())
