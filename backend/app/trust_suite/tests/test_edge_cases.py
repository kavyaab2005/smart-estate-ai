import unittest
from app.trust_suite.services.normalize import (
    normalize_name,
    names_match,
    normalize_survey_number,
    parse_date,
    to_sqft,
    areas_match,
)
from app.trust_suite.services.doc_types import (
    normalize_doc_type,
    detect_rtc,
    DocType,
    UnsupportedDocumentType,
)


class TestEdgeCases(unittest.TestCase):

    def test_names_match_so_variants_matched(self):
        """Ramesh Kumar vs RAMESH KUMAR S/O Gopal should be matched"""
        status, score = names_match("Ramesh Kumar", "RAMESH KUMAR S/O Gopal")
        self.assertEqual(status, "matched")
        self.assertEqual(score, 100.0)

    def test_names_match_initial_vs_full_not_hard_mismatch(self):
        """R Kumar vs Ramesh Kumar should not be hard mismatch"""
        status, score = names_match("R Kumar", "Ramesh Kumar")
        self.assertIn(status, ["matched", "needs_manual_verification"])
        self.assertGreater(score, 60.0)

    def test_normalize_survey_sy_no_vs_survey_no_equal(self):
        self.assertEqual(normalize_survey_number("Sy.No 45/2"), normalize_survey_number("Survey No. 45/2"))

    def test_normalize_survey_45_2_vs_45_3_different(self):
        self.assertNotEqual(normalize_survey_number("45/2"), normalize_survey_number("45/3"))

    def test_normalize_survey_45_2_vs_45_2A_different(self):
        self.assertNotEqual(normalize_survey_number("45/2"), normalize_survey_number("45/2A"))

    def test_areas_match_1200_vs_1300_mismatch(self):
        is_match, pct = areas_match(1200.0, 1300.0, tolerance=0.05)
        self.assertFalse(is_match)
        self.assertGreater(pct, 5.0)

    def test_areas_match_1200_vs_1230_match(self):
        is_match, pct = areas_match(1200.0, 1230.0, tolerance=0.05)
        self.assertTrue(is_match)
        self.assertLess(pct, 5.0)

    def test_to_sqft_fractional_guntas(self):
        self.assertEqual(to_sqft(2.5, "guntas"), 2722.5)

    def test_normalize_name_none_empty_whitespace(self):
        for val in [None, "", "   "]:
            self.assertEqual(normalize_name(val), "")
            status, score = names_match(val, "something")
            self.assertNotEqual(status, "matched")
            self.assertEqual(score, 0.0)

    def test_names_match_none_empty_whitespace(self):
        for val in [None, "", "   "]:
            status, score = names_match("something", val)
            self.assertNotEqual(status, "matched")
            self.assertEqual(score, 0.0)

    def test_normalize_survey_number_none_empty_whitespace(self):
        for val in [None, "", "   "]:
            self.assertEqual(normalize_survey_number(val), "")

    def test_parse_date_none_empty_whitespace(self):
        for val in [None, "", "   "]:
            self.assertIsNone(parse_date(val))

    def test_to_sqft_none_empty_whitespace(self):
        for val in [None, "", "   "]:
            self.assertEqual(to_sqft(100, val), 100.0)
            self.assertEqual(to_sqft(0, val), 0.0)

    def test_areas_match_none_zero_negative(self):
        is_match, pct = areas_match(0, 100)
        self.assertFalse(is_match)
        is_match, pct = areas_match(-10, 100)
        self.assertFalse(is_match)
        is_match, pct = areas_match(100, 0)
        self.assertFalse(is_match)

    def test_normalize_doc_type_none_empty_whitespace(self):
        for val in [None, "", "   "]:
            self.assertEqual(normalize_doc_type(val), DocType.OTHER)

    def test_detect_rtc_none_empty_whitespace(self):
        for val in [None, "", "   "]:
            self.assertFalse(detect_rtc(val))

    def test_parse_date_dd_mm_yyyy_day_first(self):
        d = parse_date("12/03/2019")
        self.assertIsNotNone(d)
        self.assertEqual(d.day, 12)
        self.assertEqual(d.month, 3)
        self.assertEqual(d.year, 2019)

    def test_parse_date_impossible_returns_none(self):
        self.assertIsNone(parse_date("31/02/2019"))
        self.assertIsNone(parse_date("31/04/2019"))
        self.assertIsNone(parse_date("31/06/2019"))
        self.assertIsNone(parse_date("31/09/2019"))
        self.assertIsNone(parse_date("31/11/2019"))


if __name__ == "__main__":
    unittest.main()
