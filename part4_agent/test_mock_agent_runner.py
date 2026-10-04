"""Agent-level Given-When-Then specs for mock_agent_runner. Run: python -m unittest -v test_mock_agent_runner"""
import csv
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from mock_agent_runner import run  # noqa: E402  (also puts part2/part3 on sys.path)
from growth_engine import mom_growth  # noqa: E402
from template_fill import build_inputs, draft_message, fill_prompt, untraceable_numbers  # noqa: E402

DATA = os.path.join(HERE, "data")
FIX = os.path.join(HERE, "fixtures")
CORRUPTED = os.path.join(ROOT, "part2_engine", "fixtures", "corrupted_feed.csv")
PART1 = os.path.join(ROOT, "part1_sql", "output", "monthly_category_revenue.csv")
KEYS = {"run_month", "validation_status", "validation_errors", "flagged_categories",
        "suppressed_categories", "escalated_categories", "action_taken"}
NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def feed(name):
    return os.path.join(DATA, name + ".csv")


def revenue(name, category):
    with open(feed(name), newline="") as f:
        return next(float(r["revenue"]) for r in csv.DictReader(f) if r["category"] == category)


def write_tmp(directory, name, text):
    path = os.path.join(directory, name)
    with open(path, "w") as f:
        f.write(text)
    return path


class TestAgentSpecs(unittest.TestCase):
    # ---- the four Part 2 specs, phrased at agent level ----------------------

    def test_spec1_ethnic_wear_may_is_flagged_and_drafted(self):
        # GIVEN April->May Ethnic Wear revenue moves from 104520.77 to 185107.61
        self.assertEqual(revenue("april", "Ethnic Wear"), 104520.77)
        self.assertEqual(revenue("may", "Ethnic Wear"), 185107.61)
        # WHEN the agent runs for May
        out = run("May", feed("april"), feed("may"))
        # THEN Ethnic Wear is flagged at 77.1 and, being the largest move, is drafted first
        first = out["flagged_categories"][0]
        self.assertEqual((first["category"], first["mom_pct"], first["drafted"]),
                         ("Ethnic Wear", 77.1, True))
        self.assertIn("message", first)

    def test_spec2_beauty_june_is_not_flagged(self):
        # GIVEN May->June Beauty & Personal Care revenue moves from 35542.11 to 37559.07
        self.assertEqual(revenue("may", "Beauty & Personal Care"), 35542.11)
        self.assertEqual(revenue("june", "Beauty & Personal Care"), 37559.07)
        # WHEN the agent runs for June
        out = run("June", feed("may"), feed("june"))
        # THEN its 5.67 growth is not flagged, suppressed or escalated, and no draft exists
        self.assertEqual(mom_growth(35542.11, 37559.07), 5.67)
        name = "Beauty & Personal Care"
        self.assertNotIn(name, [c["category"] for c in out["flagged_categories"]])
        self.assertNotIn(name, out["suppressed_categories"])
        self.assertNotIn(name, out["escalated_categories"])

    def test_spec3_exact_boundary_is_escalated_not_decided(self):
        # GIVEN a synthetic category moving from 100000 to 108000 (exactly 8.0%)
        # WHEN the agent runs
        out = run("August", os.path.join(FIX, "boundary_prev.csv"),
                  os.path.join(FIX, "boundary_curr.csv"))
        # THEN it is escalated, and is neither flagged, suppressed nor drafted
        self.assertEqual(out["escalated_categories"], ["Synthetic Boundary"])
        self.assertNotIn("Synthetic Boundary", [c["category"] for c in out["flagged_categories"]])
        self.assertNotIn("Synthetic Boundary", out["suppressed_categories"])
        # AND a genuinely flagged category in the same run is still drafted
        self.assertEqual([c["category"] for c in out["flagged_categories"]], ["Synthetic Flagged"])

    def test_spec4_corrupted_feed_is_a_hard_stop(self):
        # GIVEN the corrupted feed fixture as the current month
        # WHEN the agent runs
        out = run("July", feed("april"), CORRUPTED)
        # THEN it hard-stops with exactly the 3 errors in order and drafts nothing
        self.assertEqual(out["validation_status"], "invalid")
        self.assertEqual(out["action_taken"], "hard_stop")
        self.assertEqual(out["validation_errors"], [
            "line 3: negative revenue (-4200.00) for category=Western Wear",
            "line 4: missing category (month=July)",
            "line 6: missing revenue (category=Home & Kitchen)",
        ])
        self.assertEqual((out["flagged_categories"], out["suppressed_categories"],
                          out["escalated_categories"]), ([], [], []))

    # ---- planner behaviour --------------------------------------------------

    def test_may_scenario_caps_drafts_at_three_and_suppresses_the_rest(self):
        out = run("May", feed("april"), feed("may"))
        self.assertEqual([c["category"] for c in out["flagged_categories"]],
                         ["Ethnic Wear", "Western Wear", "Kids Wear",
                          "Beauty & Personal Care", "Home & Kitchen"])
        self.assertEqual([c["drafted"] for c in out["flagged_categories"]],
                         [True, True, True, False, False])
        self.assertEqual(out["suppressed_categories"], ["Beauty & Personal Care", "Home & Kitchen"])
        self.assertEqual(out["escalated_categories"], [])
        self.assertNotIn("message", out["flagged_categories"][3])

    def test_june_scenario_ethnic_wear_decline_is_flagged_first(self):
        out = run("June", feed("may"), feed("june"))
        self.assertEqual([(c["category"], c["mom_pct"]) for c in out["flagged_categories"]],
                         [("Ethnic Wear", -58.74), ("Home & Kitchen", 42.59),
                          ("Kids Wear", 23.9), ("Western Wear", 11.97)])
        self.assertEqual(out["suppressed_categories"], ["Western Wear"])
        self.assertEqual(out["escalated_categories"], [])

    def test_no_flagged_categories_gives_valid_run_with_zero_drafts(self):
        out = run("April", feed("april"), feed("april"))
        self.assertEqual(out["validation_status"], "valid")
        self.assertEqual((out["flagged_categories"], out["suppressed_categories"]), ([], []))
        self.assertEqual(out["action_taken"], "drafted_and_held_for_approval")

    # ---- schema and guardrails ---------------------------------------------

    def test_every_run_emits_exactly_the_schema_keys(self):
        runs = [run("May", feed("april"), feed("may")),
                run("July", feed("april"), CORRUPTED)]
        for out in runs:
            self.assertEqual(set(out), KEYS)
            self.assertIn(out["validation_status"], ("valid", "invalid"))
            self.assertIn(out["action_taken"], ("drafted_and_held_for_approval", "hard_stop"))

    def test_every_number_in_every_draft_traces_to_part1_part2_values(self):
        for month, prev, cur in [("May", "april", "may"), ("June", "may", "june")]:
            out = run(month, feed(prev), feed(cur))
            for c in out["flagged_categories"]:
                if not c["drafted"]:
                    continue
                p, q = revenue(prev, c["category"]), revenue(cur, c["category"])
                allowed = {f"{p:,.2f}", f"{q:,.2f}", str(mom_growth(p, q)), "8.0"}
                with open(feed(prev), newline="") as f1, open(feed(cur), newline="") as f2:
                    allowed.add(next(r["n_orders"] for r in csv.DictReader(f1) if r["category"] == c["category"]))
                    allowed.add(next(r["n_orders"] for r in csv.DictReader(f2) if r["category"] == c["category"]))
                self.assertEqual(set(NUM.findall(c["message"])) - allowed, set(), c["category"])

    def test_previous_feed_errors_are_prefixed_so_the_source_is_clear(self):
        out = run("May", CORRUPTED, feed("may"))
        self.assertEqual(out["action_taken"], "hard_stop")
        self.assertTrue(all(e.startswith("previous_month_csv: ") for e in out["validation_errors"]))

    def test_unpairable_feeds_hard_stop_instead_of_crashing(self):
        header = "month,category,revenue,n_orders\n"
        with tempfile.TemporaryDirectory() as d:
            prev = write_tmp(d, "p.csv", header + "April,A,0.00,5\nApril,B,100.00,5\n")
            cur = write_tmp(d, "c.csv", header + "May,A,50.00,5\nMay,C,100.00,5\n")
            out = run("May", prev, cur)
        self.assertEqual((out["validation_status"], out["action_taken"]), ("invalid", "hard_stop"))
        joined = " | ".join(out["validation_errors"])
        self.assertIn("category sets differ", joined)
        self.assertIn("previous revenue is 0", joined)

    def test_month_label_mismatch_hard_stops(self):
        out = run("June", feed("april"), feed("may"))
        self.assertEqual(out["action_taken"], "hard_stop")
        self.assertIn("expected month 'June'", out["validation_errors"][0])

    def test_runner_has_no_network_or_mail_code(self):
        src = open(os.path.join(HERE, "mock_agent_runner.py"), encoding="utf-8").read()
        for word in ("smtplib", "socket", "requests", "urllib", "http.client", "api_key"):
            self.assertNotIn(word, src)

    # ---- supporting data and Part 3 template -------------------------------

    def test_month_feeds_are_exact_splits_of_the_part1_output(self):
        with open(PART1, newline="") as f:
            rows = list(csv.DictReader(f))
        for month in ("April", "May", "June"):
            with open(feed(month.lower()), newline="") as f:
                self.assertEqual(list(csv.DictReader(f)), [r for r in rows if r["month"] == month])

    def test_prompt_template_fills_fully_and_rejects_missing_input(self):
        inputs = build_inputs("Ethnic Wear", "April", "May", 104520.77, 185107.61, 77.1, 64, 104)
        prompt = fill_prompt(inputs)
        self.assertNotRegex(prompt, r"\{[a-z_]+\}")
        self.assertIn("INR 185,107.61", prompt)
        broken = dict(inputs, mom_pct="")
        with self.assertRaisesRegex(ValueError, "MISSING INPUT: mom_pct"):
            fill_prompt(broken)

    def test_draft_matches_worked_narrative_numbers_and_flags_untraceable_text(self):
        inputs = build_inputs("Ethnic Wear", "May", "June", 185107.61, 76371.53, -58.74, 104, 52)
        text = draft_message(inputs)
        self.assertEqual(untraceable_numbers(text, inputs), [])
        self.assertEqual(untraceable_numbers(text + " Revenue was 99,999.", inputs), ["99,999"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
