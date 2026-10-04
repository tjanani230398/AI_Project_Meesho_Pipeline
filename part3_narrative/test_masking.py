"""Given-When-Then tests for masking.py. Run: python -m unittest -v test_masking"""
import os
import re
import sqlite3
import unittest

from masking import alias_for, assert_no_raw_names_leak

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "..", "part1_sql", "meesho_reseller.db")
REPORT = os.path.join(HERE, "narrative_report.md")


def all_reseller_names():
    conn = sqlite3.connect(DB)
    try:
        return [r[0] for r in conn.execute("SELECT reseller_name FROM resellers")]
    finally:
        conn.close()


class TestMasking(unittest.TestCase):
    def test_alias_for_strips_prefix_and_keeps_leading_zero(self):
        # GIVEN reseller ids RS019 and RS006  WHEN aliased  THEN ALIAS-19 and ALIAS-06
        self.assertEqual(alias_for("RS019"), "ALIAS-19")
        self.assertEqual(alias_for("RS006"), "ALIAS-06")

    def test_leak_is_detected(self):
        # GIVEN text naming a reseller verbatim  WHEN checked  THEN it returns False
        names = all_reseller_names()
        self.assertFalse(assert_no_raw_names_leak(f"Top spender was {names[0]}.", names))

    def test_aliased_text_is_clean(self):
        # GIVEN text using only alias and region  WHEN checked  THEN it returns True
        names = all_reseller_names()
        self.assertTrue(assert_no_raw_names_leak("ALIAS-19 (West) led spend.", names))

    def test_blank_name_does_not_cause_false_alarm(self):
        # GIVEN a blank name in the list  WHEN checked  THEN it is ignored
        self.assertTrue(assert_no_raw_names_leak("ALIAS-19 (West)", [""]))

    def test_final_top_reseller_narrative_has_no_raw_names(self):
        # GIVEN the final narrative report  WHEN checked against all 24 names  THEN True
        text = open(REPORT, encoding="utf-8").read()
        self.assertTrue(assert_no_raw_names_leak(text, all_reseller_names()))
        # AND every top-5 reseller appears by alias
        for rid in ["RS019", "RS022", "RS012", "RS006", "RS005"]:
            self.assertIn(alias_for(rid), text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
