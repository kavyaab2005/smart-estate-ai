import unittest
from uuid import uuid4
from app.trust_suite.schemas import TrustFindingSchema, TrustAdminChecklistItem, FindingEvidence
from app.trust_suite.services.score import compute_score, ScoreBreakdown


class TestComputeScore(unittest.TestCase):

    def _make_finding(self, check_id: str, category: str, severity: str, status: str, field: str = None) -> TrustFindingSchema:
        return TrustFindingSchema(
            check_id=check_id,
            category=category,
            severity=severity,
            status=status,
            field=field,
            evidence=[],
            why_raised="test",
            next_step="test",
            seller_message=None,
        )

    def _make_checklist_item(self, item_key: str, is_applicable: bool = True, verified: bool = False, note: str = None) -> TrustAdminChecklistItem:
        return TrustAdminChecklistItem(
            item_key=item_key,
            label=item_key.replace("_", " ").title(),
            is_applicable=is_applicable,
            verified=verified,
            note=note,
            evidence_doc_ids=[],
        )

    def test_automated_basic_passed_and_total(self):
        """Automated consistency checks: passed and total counted correctly."""
        findings = [
            self._make_finding("owner_name", "consistency", "info", "matched", "owner_name"),
            self._make_finding("survey_number", "consistency", "info", "matched", "survey_number"),
            self._make_finding("area", "consistency", "info", "mismatch", "area"),
        ]
        checklist = [
            self._make_checklist_item("owner_name_matched", True, True, "verified"),
        ]
        result = compute_score(findings, checklist, [])
        self.assertEqual(result.automated_checks_total, 3)
        self.assertEqual(result.automated_checks_passed, 2)
        self.assertEqual(result.admin_checks_total, 1)
        self.assertEqual(result.admin_checks_passed, 1)

    def test_missing_document_counts_in_total_not_passed(self):
        """Rule 2: Missing document checks count in total but not passed."""
        findings = [
            self._make_finding("owner_name", "consistency", "info", "matched", "owner_name"),
            self._make_finding("survey_number", "consistency", "info", "needs_manual_verification", "survey_number"),
        ]
        checklist = [
            self._make_checklist_item("owner_name_matched", True, True, "ok"),
        ]
        result = compute_score(findings, checklist, ["encumbrance_certificate"])
        self.assertEqual(result.automated_checks_total, 2)
        self.assertEqual(result.automated_checks_passed, 1)
        self.assertIn("encumbrance_certificate", result.breakdown_json["missing_documents"])

    def test_not_applicable_removed_from_both(self):
        """Rule 3: Not-applicable items leave both total and passed."""
        findings = [
            self._make_finding("owner_name", "consistency", "info", "matched", "owner_name"),
        ]
        checklist = [
            self._make_checklist_item("owner_name_matched", True, True, "ok"),
            self._make_checklist_item("survey_number_matched", False, False, "not applicable - no survey"),
            self._make_checklist_item("area_matched", False, False, "not applicable - no area"),
        ]
        result = compute_score(findings, checklist, [])
        self.assertEqual(result.admin_checks_total, 1)
        self.assertEqual(result.admin_checks_passed, 1)

    def test_not_applicable_without_note_raises_error(self):
        """Rule 3: Not-applicable without a note is an error."""
        findings = [
            self._make_finding("owner_name", "consistency", "info", "matched", "owner_name"),
        ]
        checklist = [
            self._make_checklist_item("owner_name_matched", True, True, "ok"),
            self._make_checklist_item("survey_number_matched", False, False, ""),
        ]
        with self.assertRaises(ValueError) as ctx:
            compute_score(findings, checklist, [])
        self.assertIn("not applicable without a note", str(ctx.exception))

    def test_not_applicable_with_whitespace_note_raises_error(self):
        """Not-applicable with only whitespace note is an error."""
        findings = [
            self._make_finding("owner_name", "consistency", "info", "matched", "owner_name"),
        ]
        checklist = [
            self._make_checklist_item("owner_name_matched", True, True, "ok"),
            self._make_checklist_item("survey_number_matched", False, False, "   "),
        ]
        with self.assertRaises(ValueError) as ctx:
            compute_score(findings, checklist, [])
        self.assertIn("not applicable without a note", str(ctx.exception))

    def test_integrity_indicator_does_not_change_score(self):
        """Rule 4: Integrity indicators never change any number."""
        findings = [
            self._make_finding("owner_name", "consistency", "info", "matched", "owner_name"),
            self._make_finding("missing_page", "integrity", "warning", "needs_manual_verification", "page_2"),
            self._make_finding("scan_quality", "integrity", "info", "needs_manual_verification", "scan"),
        ]
        checklist = [
            self._make_checklist_item("owner_name_matched", True, True, "ok"),
        ]
        result = compute_score(findings, checklist, [])
        self.assertEqual(result.automated_checks_total, 1)
        self.assertEqual(result.automated_checks_passed, 1)
        self.assertEqual(result.admin_checks_total, 1)
        self.assertEqual(result.admin_checks_passed, 1)

    def test_display_text_exact_counts(self):
        """Display text shows exact counts like '4 of 6 verified', never rounded up."""
        findings = [
            self._make_finding("owner_name", "consistency", "info", "matched", "owner_name"),
        ]
        checklist = [
            self._make_checklist_item("owner_name_matched", True, True, "ok"),
            self._make_checklist_item("survey_number_matched", True, True, "ok"),
            self._make_checklist_item("area_matched", True, False, "mismatch"),
            self._make_checklist_item("ec_checked", True, True, "ok"),
            self._make_checklist_item("registration_details_checked", True, True, "ok"),
            self._make_checklist_item("dues_checked", True, False, "pending"),
        ]
        result = compute_score(findings, checklist, [])
        self.assertEqual(result.display_text, "4 of 6 verified")
        self.assertEqual(result.admin_checks_total, 6)
        self.assertEqual(result.admin_checks_passed, 4)

    def test_disclaimer_included(self):
        """Rule 7: Disclaimer appears in output."""
        findings = [
            self._make_finding("owner_name", "consistency", "info", "matched", "owner_name"),
        ]
        checklist = [
            self._make_checklist_item("owner_name_matched", True, True, "ok"),
        ]
        result = compute_score(findings, checklist, [])
        self.assertEqual(result.disclaimer, "This is a consistency and verification summary, not legal advice or proof of title. Consult an advocate before paying or registering.")

    def test_score_percentage_dict_two_parts(self):
        """Score percentage returned as dict with two separate parts."""
        findings = [
            self._make_finding("owner_name", "consistency", "info", "matched", "owner_name"),
            self._make_finding("survey_number", "consistency", "info", "mismatch", "survey_number"),
        ]
        checklist = [
            self._make_checklist_item("owner_name_matched", True, True, "ok"),
            self._make_checklist_item("survey_number_matched", True, False, "mismatch"),
        ]
        result = compute_score(findings, checklist, [])
        self.assertIn("automated", result.score_percentage)
        self.assertIn("admin", result.score_percentage)
        self.assertEqual(result.score_percentage["automated"], 50.0)
        self.assertEqual(result.score_percentage["admin"], 50.0)

    def test_breakdown_json_structure(self):
        """breakdown_json contains automated, admin, and missing_documents."""
        findings = [
            self._make_finding("owner_name", "consistency", "info", "matched", "owner_name"),
        ]
        checklist = [
            self._make_checklist_item("owner_name_matched", True, True, "ok"),
        ]
        result = compute_score(findings, checklist, ["encumbrance_certificate"])
        self.assertIn("automated", result.breakdown_json)
        self.assertIn("admin", result.breakdown_json)
        self.assertIn("missing_documents", result.breakdown_json)
        self.assertEqual(result.breakdown_json["missing_documents"], ["encumbrance_certificate"])

    def test_zero_automated_checks(self):
        """Handle case with zero automated checks."""
        findings = []
        checklist = [
            self._make_checklist_item("owner_name_matched", True, True, "ok"),
        ]
        result = compute_score(findings, checklist, [])
        self.assertEqual(result.automated_checks_total, 0)
        self.assertEqual(result.automated_checks_passed, 0)
        self.assertEqual(result.score_percentage["automated"], 0.0)

    def test_zero_admin_checks(self):
        """Handle case with zero admin checks (all not applicable)."""
        findings = [
            self._make_finding("owner_name", "consistency", "info", "matched", "owner_name"),
        ]
        checklist = [
            self._make_checklist_item("owner_name_matched", False, False, "not applicable"),
            self._make_checklist_item("survey_number_matched", False, False, "not applicable"),
        ]
        result = compute_score(findings, checklist, [])
        self.assertEqual(result.admin_checks_total, 0)
        self.assertEqual(result.admin_checks_passed, 0)
        self.assertEqual(result.score_percentage["admin"], 0.0)

    def test_completeness_category_not_counted_in_automated(self):
        """Completeness findings don't count as automated consistency checks."""
        findings = [
            self._make_finding("owner_name", "consistency", "info", "matched", "owner_name"),
            self._make_finding("missing_doc", "completeness", "warning", "needs_manual_verification", "doc"),
        ]
        checklist = [
            self._make_checklist_item("owner_name_matched", True, True, "ok"),
        ]
        result = compute_score(findings, checklist, [])
        self.assertEqual(result.automated_checks_total, 1)
        self.assertEqual(result.automated_checks_passed, 1)


if __name__ == "__main__":
    unittest.main()