"""Given-When-Then tests for growth_engine. Run: python -m unittest -v test_growth_engine"""
import os
import tempfile
import unittest

from growth_engine import is_flagged, mom_growth, validate_feed

HERE = os.path.dirname(os.path.abspath(__file__))
CORRUPTED_FEED = os.path.join(HERE, "fixtures", "corrupted_feed.csv")
CLEAN_FEED = os.path.join(HERE, "fixtures", "monthly_category_revenue.csv")


class TestGrowthEngine(unittest.TestCase):
    def test_ethnic_wear_april_to_may_is_flagged(self):
        # GIVEN Ethnic Wear revenue moves from 104520.77 (April) to 185107.61 (May)
        previous, current = 104520.77, 185107.61
        # WHEN mom_growth then is_flagged run on it
        growth = mom_growth(previous, current)
        verdict = is_flagged(growth)
        # THEN growth is 77.1 and it is flagged
        self.assertEqual(growth, 77.1)
        self.assertEqual(verdict, "flagged")

    def test_beauty_may_to_june_is_not_flagged(self):
        # GIVEN Beauty & Personal Care revenue moves from 35542.11 to 37559.07
        previous, current = 35542.11, 37559.07
        # WHEN evaluated
        growth = mom_growth(previous, current)
        verdict = is_flagged(growth)
        # THEN growth is 5.67 and it is not flagged
        self.assertEqual(growth, 5.67)
        self.assertEqual(verdict, "not_flagged")

    def test_exact_boundary_is_escalated_not_decided(self):
        # GIVEN a synthetic pair landing exactly on the 8.0 threshold
        previous, current = 100000, 108000
        # WHEN evaluated
        growth = mom_growth(previous, current)
        verdict = is_flagged(growth)
        # THEN growth is exactly 8.0 and the case is escalated, never auto-decided
        self.assertEqual(growth, 8.0)
        self.assertEqual(verdict, "escalate_exact_boundary")
        self.assertNotIn(verdict, ("flagged", "not_flagged"))

    def test_corrupted_feed_reports_three_errors_in_order(self):
        # GIVEN the corrupted feed fixture
        # WHEN validate_feed runs on it
        ok, errors = validate_feed(CORRUPTED_FEED)
        # THEN it fails with exactly 3 errors: negative revenue, missing category,
        # missing revenue -- in file order
        self.assertIs(ok, False)
        self.assertEqual(errors, [
            "line 3: negative revenue (-4200.00) for category=Western Wear",
            "line 4: missing category (month=July)",
            "line 6: missing revenue (category=Home & Kitchen)",
        ])

    # --- extra edge cases ---------------------------------------------------

    def test_decline_beyond_threshold_is_flagged(self):
        # GIVEN revenue falls 20%  WHEN evaluated  THEN the magnitude triggers a flag
        self.assertEqual(is_flagged(mom_growth(1000, 800)), "flagged")

    def test_negative_exact_boundary_is_escalated(self):
        # GIVEN a decline of exactly 8%  WHEN evaluated  THEN it is also escalated
        self.assertEqual(is_flagged(mom_growth(100000, 92000)), "escalate_exact_boundary")

    def test_custom_threshold_is_respected(self):
        # GIVEN 5.67% growth and a stricter 5.0 threshold  THEN it is flagged
        self.assertEqual(is_flagged(5.67, threshold=5.0), "flagged")

    def test_non_numeric_revenue_is_reported(self):
        # GIVEN a feed with revenue "abc"  WHEN validated  THEN it is reported with repr()
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "feed.csv")
            with open(p, "w") as f:
                f.write("month,category,revenue,n_orders\nApril,Kids Wear,abc,5\n")
            self.assertEqual(validate_feed(p),
                             (False, ["line 2: revenue not numeric: 'abc'"]))

    def test_clean_feed_passes(self):
        # GIVEN the validated Part 1 output  WHEN validated  THEN (True, [])
        self.assertEqual(validate_feed(CLEAN_FEED), (True, []))


if __name__ == "__main__":
    unittest.main(verbosity=2)
