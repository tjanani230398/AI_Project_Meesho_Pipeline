"""Template-fill logic for the Part 3 prompt pack. No model or network call.

- load_prompt_template(): reads the prompt text straight out of prompt_pack.md
  (single source of truth).
- build_inputs(): turns verified numbers into the pack's display-string placeholders.
- fill_prompt(): fills the pack's prompt (what a real model call would receive).
- draft_message(): deterministic stand-in for the model's answer, written to obey the
  pack's rules (Context/Insight/Implication, [Fact]/[Hypothesis]/[Action] labels, only
  supplied numbers, no reseller names).
- untraceable_numbers(): output check, every number must be a supplied placeholder.
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PACK_PATH = os.path.join(HERE, "prompt_pack.md")

REQUIRED = ["category", "prev_month", "month", "previous_revenue", "current_revenue",
            "mom_pct", "direction", "threshold", "prev_n_orders", "current_n_orders"]
NUMERIC_KEYS = ["previous_revenue", "current_revenue", "mom_pct", "threshold",
                "prev_n_orders", "current_n_orders"]
_NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def load_prompt_template(path: str = PACK_PATH) -> str:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    section = text.split("## 3. Prompt", 1)[1]
    match = re.search(r"```text\n(.*?)\n```", section, re.S)
    if not match:
        raise ValueError("prompt block not found in prompt_pack.md")
    return match.group(1)


def build_inputs(category, prev_month, month, previous_revenue, current_revenue,
                 mom_pct, prev_n_orders, current_n_orders, threshold=8.0) -> dict:
    if mom_pct == 0:
        raise ValueError("mom_pct is 0: nothing to flag")
    return {
        "category": category,
        "prev_month": prev_month,
        "month": month,
        "previous_revenue": f"{previous_revenue:,.2f}",
        "current_revenue": f"{current_revenue:,.2f}",
        "mom_pct": str(mom_pct),
        "direction": "rose" if mom_pct > 0 else "fell",
        "threshold": f"{threshold:.1f}",
        "prev_n_orders": str(prev_n_orders),
        "current_n_orders": str(current_n_orders),
    }


def fill_prompt(inputs: dict) -> str:
    for name in REQUIRED:
        if not str(inputs.get(name, "")).strip():
            raise ValueError(f"MISSING INPUT: {name}")
    return load_prompt_template().format(**inputs)


def draft_message(inputs: dict) -> str:
    fill_prompt(inputs)  # validates that every placeholder is present
    i = inputs
    rose = i["direction"] == "rose"
    prev_o, cur_o = int(i["prev_n_orders"]), int(i["current_n_orders"])
    volume_driven = cur_o != prev_o and ((cur_o > prev_o) == rose)

    if volume_driven and rose:
        cause = (f"The rise may reflect a {i['month']}-specific demand driver, such as a "
                 f"promotion or seasonal push, because orders and revenue moved together")
        action1 = (f"Ask the regional leads whether any {i['category']} promotion or seasonal "
                   f"stocking ran in {i['month']}; if none did, find another explanation "
                   f"before {i['month']} is used as a planning baseline.")
    elif volume_driven:
        cause = (f"The fall may be the {i['prev_month']} demand driver ending, rather than a "
                 f"new weakness, because orders and revenue moved together")
        action1 = (f"Ask the regional leads whether the {i['prev_month']} {i['category']} "
                   f"promotion or seasonal demand ended, and whether any {i['month']} stock "
                   f"shortage held back {i['category']} orders.")
    else:
        shift = "higher-priced or larger" if rose else "lower-priced or smaller"
        cause = (f"The change may reflect a shift to {shift} orders, because orders did not "
                 f"move in step with revenue")
        action1 = (f"Compare the {i['category']} items and prices sold in {i['prev_month']} "
                   f"and {i['month']}; if a few large or discounted items explain the change, "
                   f"treat {i['month']} as unrepresentative until it repeats.")

    if rose:
        action2 = (f"Split {i['month']}'s INR {i['current_revenue']} by order status "
                   f"(delivered, returned, cancelled, pending); if delivered revenue is much "
                   f"lower, treat the {i['mom_pct']}% change as overstated.")
    else:
        action2 = (f"Compare {i['month']}'s {i['category']} orders with {i['prev_month']}'s "
                   f"region by region: a drop concentrated in one region points to a local "
                   f"problem to fix, while an even drop points to a change in demand.")

    return (
        f"Context: This update looks at {i['category']} revenue in {i['month']} vs. "
        f"{i['prev_month']}. Any month-on-month change above {i['threshold']}% in either "
        f"direction is reviewed.\n"
        f"Insight: [Fact] {i['category']} revenue {i['direction']} from INR "
        f"{i['previous_revenue']} in {i['prev_month']} to INR {i['current_revenue']} in "
        f"{i['month']}, a change of {i['mom_pct']}%. [Fact] Orders went from "
        f"{i['prev_n_orders']} to {i['current_n_orders']} over the same period.\n"
        f"Implication: [Hypothesis] {cause}; the figures alone do not show why. "
        f"[Action] {action1} [Action] {action2}"
    )


def untraceable_numbers(text: str, inputs: dict) -> list:
    """Numbers in text that are not one of the supplied placeholder values."""
    allowed = {inputs[k] for k in NUMERIC_KEYS}
    return sorted(set(_NUM.findall(text)) - allowed)
