import unittest
from app.trust_suite.services.normalize import (
    normalize_name,
    names_match,
    normalize_survey_number,
    parse_date,
    to_sqft,
    areas_match,
)


class TestNormalize(unittest.TestCase):

    def test_normalize_name_basic(self):
        self.assertEqual(normalize_name("Ramesh Kumar"), "RAMESH KUMAR")
        self.assertEqual(normalize_name("  ramesh  kumar  "), "RAMESH KUMAR")

    def test_normalize_name_honorifics(self):
        self.assertEqual(normalize_name("Mr. Ramesh Kumar"), "RAMESH KUMAR")
        self.assertEqual(normalize_name("Mrs. Ramesh Kumar"), "RAMESH KUMAR")
        self.assertEqual(normalize_name("Shri Ramesh Kumar"), "RAMESH KUMAR")
        self.assertEqual(normalize_name("Smt. Ramesh Kumar"), "RAMESH KUMAR")
        self.assertEqual(normalize_name("Sri Ramesh Kumar"), "RAMESH KUMAR")

    def test_normalize_name_so_do_wo(self):
        self.assertEqual(normalize_name("Ramesh S/O Gopal"), "RAMESH")
        self.assertEqual(normalize_name("Ramesh D/O Gopal"), "RAMESH")
        self.assertEqual(normalize_name("Ramesh W/O Gopal"), "RAMESH")
        self.assertEqual(normalize_name("Ramesh C/O Gopal"), "RAMESH")

    def test_normalize_name_initials(self):
        self.assertEqual(normalize_name("R. K. Sharma"), "R K SHARMA")
        self.assertEqual(normalize_name("R.K. Sharma"), "R K SHARMA")

    def test_names_match_exact(self):
        status, score = names_match("Ramesh Kumar", "RAMESH KUMAR")
        self.assertEqual(status, "matched")
        self.assertEqual(score, 100.0)

    def test_names_match_with_so(self):
        status, score = names_match("Ramesh Kumar", "RAMESH KUMAR S/O GOPAL")
        self.assertEqual(status, "matched")
        self.assertEqual(score, 100.0)

    def test_names_match_initial_vs_full(self):
        status, score = names_match("R K Sharma", "RAMESH KUMAR SHARMA")
        self.assertIn(status, ["matched", "needs_manual_verification"])
        self.assertGreater(score, 60.0)

    def test_names_match_mismatch(self):
        status, score = names_match("Ramesh Kumar", "Suresh Patel")
        self.assertEqual(status, "mismatch")
        self.assertLess(score, 60.0)

    def test_normalize_survey_number(self):
        self.assertEqual(normalize_survey_number("Sy.No 45/2"), "45/2")
        self.assertEqual(normalize_survey_number("45-2"), "45/2")
        self.assertEqual(normalize_survey_number("Survey No. 45/2"), "45/2")
        self.assertEqual(normalize_survey_number("  123/4A  "), "123/4A")

    def test_parse_date_dd_mm_yyyy(self):
        self.assertEqual(parse_date("15/08/2023"), parse_date("15-08-2023"))
        self.assertEqual(parse_date("1/1/2020"), parse_date("01/01/2020"))

    def test_parse_date_yyyy_mm_dd(self):
        self.assertEqual(parse_date("2023-08-15"), parse_date("2023/08/15"))

    def test_parse_date_dd_mm_yy(self):
        self.assertEqual(parse_date("15/08/23"), parse_date("15-08-23"))

    def test_parse_date_month_name(self):
        self.assertEqual(parse_date("12 March 2019"), parse_date("12 Mar 2019"))
        self.assertEqual(parse_date("12-March-2019"), parse_date("12 March 2019"))

    def test_to_sqft_sqft(self):
        self.assertEqual(to_sqft(1000, "sqft"), 1000.0)
        self.assertEqual(to_sqft(1000, "sq ft"), 1000.0)

    def test_to_sqft_sqm(self):
        self.assertAlmostEqual(to_sqft(100, "sqm"), 1076.39, places=1)

    def test_to_sqft_guntas(self):
        self.assertEqual(to_sqft(2, "guntas"), 2178.0)
        self.assertEqual(to_sqft(40, "guntas"), 43560.0)

    def test_to_sqft_acres(self):
        self.assertEqual(to_sqft(1, "acre"), 43560.0)
        self.assertEqual(to_sqft(1, "acres"), 43560.0)

    def test_areas_match_within_tolerance(self):
        is_match, pct = areas_match(1000.0, 1020.0, tolerance=0.05)
        self.assertTrue(is_match)
        self.assertLess(pct, 5.0)

    def test_areas_match_outside_tolerance(self):
        is_match, pct = areas_match(1000.0, 1100.0, tolerance=0.05)
        self.assertFalse(is_match)
        self.assertGreater(pct, 5.0)

    def test_areas_match_zero(self):
        is_match, pct = areas_match(0.0, 1000.0)
        self.assertFalse(is_match)


if __name__ == "__main__":
    unittest.main()
