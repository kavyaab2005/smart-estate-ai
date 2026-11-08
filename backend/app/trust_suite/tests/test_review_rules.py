import unittest
from uuid import uuid4
from app.trust_suite.schemas import TrustFindingSchema, TrustAdminChecklistItem
from app.trust_suite.services.review_rules import queue_priority, validate_decision, revert_on_reupload


class TestQueuePriority(unittest.TestCase):

    def _make_finding(self, check_id: str, category: str, severity: str, status: str = "mismatch") -> TrustFindingSchema:
        return TrustFindingSchema(
            check_id=check_id,
            category=category,
            severity=severity,
            status=status,
            evidence=[],
            why_raised="test",
            next_step="test",
            seller_message=None,
        )

    def test_missing_documents_highest_priority(self):
        """Missing documents -> priority 0, flagged."""
        findings = []
        result = queue_priority(findings, ["encumbrance_certificate"])
        self.assertEqual(result.priority, 0)
        self.assertTrue(result.is_flagged)

    def test_critical_findings_priority_1(self):
        """Critical findings -> priority 1, flagged."""
        findings = [
            self._make_finding("owner_name", "consistency", "critical", "mismatch"),
        ]
        result = queue_priority(findings, [])
        self.assertEqual(result.priority, 1)
        self.assertTrue(result.is_flagged)

    def test_warning_findings_priority_2(self):
        """Warning findings -> priority 2, flagged."""
        findings = [
            self._make_finding("survey_number", "consistency", "warning", "mismatch"),
        ]
        result = queue_priority(findings, [])
        self.assertEqual(result.priority, 2)
        self.assertTrue(result.is_flagged)

    def test_info_findings_priority_3(self):
        """Info findings -> priority 3, flagged."""
        findings = [
            self._make_finding("area", "consistency", "info", "needs_manual_verification"),
        ]
        result = queue_priority(findings, [])
        self.assertEqual(result.priority, 3)
        self.assertTrue(result.is_flagged)

    def test_clean_set_priority_100_not_flagged(self):
        """Clean set (no findings, no missing) -> priority 100, not flagged, still queued."""
        findings = []
        result = queue_priority(findings, [])
        self.assertEqual(result.priority, 100)
        self.assertFalse(result.is_flagged)

    def test_mixed_severity_takes_highest(self):
        """Mixed severity takes the highest (critical > warning > info)."""
        findings = [
            self._make_finding("owner_name", "consistency", "info", "matched"),
            self._make_finding("survey_number", "consistency", "warning", "mismatch"),
            self._make_finding("area", "consistency", "critical", "mismatch"),
        ]
        result = queue_priority(findings, [])
        self.assertEqual(result.priority, 1)
        self.assertTrue(result.is_flagged)

    def test_flagged_sorts_before_clean(self):
        """Flagged sets (lower priority number) sort before clean sets."""
        flagged = queue_priority([self._make_finding("x", "consistency", "critical", "mismatch")], [])
        clean = queue_priority([], [])
        self.assertLess(flagged.priority, clean.priority)


class TestValidateDecision(unittest.TestCase):

    def _make_finding(self, check_id: str, category: str, severity: str, status: str = "mismatch") -> TrustFindingSchema:
        return TrustFindingSchema(
            check_id=check_id,
            category=category,
            severity=severity,
            status=status,
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

    def test_decision_only_allowed_in_review(self):
        """Decision only allowed when current_status == 'in_review'."""
        checklist = [self._make_checklist_item("owner_name_matched", True, True, "ok")]
        findings = []
        result = validate_decision("flagged_for_review", "approve", checklist, findings, "reason", "notes", "admin1", "owner1")
        self.assertFalse(result.ok)
        self.assertIn("in_review", result.errors[0])

    def test_approver_cannot_be_listing_owner(self):
        """Approver must NOT be the listing owner."""
        checklist = [self._make_checklist_item("owner_name_matched", True, True, "ok")]
        findings = []
        result = validate_decision("in_review", "approve", checklist, findings, "reason", "notes", "same_id", "same_id")
        self.assertFalse(result.ok)
        self.assertIn("owner", result.errors[0].lower())

    def test_reject_requires_reason(self):
        """Reject requires a non-empty reason."""
        checklist = [self._make_checklist_item("owner_name_matched", True, True, "ok")]
        findings = []
        result = validate_decision("in_review", "reject", checklist, findings, "", "notes", "admin1", "owner1")
        self.assertFalse(result.ok)
        self.assertIn("reason", result.errors[0].lower())

        result = validate_decision("in_review", "reject", checklist, findings, "   ", "notes", "admin1", "owner1")
        self.assertFalse(result.ok)
        self.assertIn("reason", result.errors[0].lower())

    def test_reject_with_reason_ok(self):
        """Reject with valid reason returns ok and new_status='rejected'."""
        checklist = [self._make_checklist_item("owner_name_matched", True, True, "ok")]
        findings = []
        result = validate_decision("in_review", "reject", checklist, findings, "Document mismatch", "notes", "admin1", "owner1")
        self.assertTrue(result.ok)
        self.assertEqual(result.new_status, "rejected")
        self.assertEqual(result.errors, [])

    def test_approve_requires_applicable_items_decided(self):
        """Approve requires every applicable item decided (verified or not verified with note)."""
        checklist = [
            self._make_checklist_item("owner_name_matched", True, True, "ok"),
            self._make_checklist_item("survey_number_matched", True, False, ""),  # not verified, no note
        ]
        findings = []
        result = validate_decision("in_review", "approve", checklist, findings, "reason", "notes", "admin1", "owner1")
        self.assertFalse(result.ok)
        self.assertIn("survey_number_matched", result.errors[0])
        self.assertIn("not verified", result.errors[0].lower())

    def test_approve_not_verified_with_note_ok(self):
        """Approve allows not verified items IF they have a note."""
        checklist = [
            self._make_checklist_item("owner_name_matched", True, True, "ok"),
            self._make_checklist_item("survey_number_matched", True, False, "survey docs missing"),
        ]
        findings = []
        result = validate_decision("in_review", "approve", checklist, findings, "reason", "notes", "admin1", "owner1")
        self.assertTrue(result.ok)
        self.assertEqual(result.new_status, "approved")

    def test_approve_critical_finding_requires_acknowledgment(self):
        """Approve requires every critical finding acknowledged with a note."""
        checklist = [
            self._make_checklist_item("owner_name_matched", True, True, "ok"),
            self._make_checklist_item("survey_number_matched", True, True, ""),  # no note for critical
        ]
        findings = [
            self._make_finding("survey_number_matched", "consistency", "critical", "mismatch"),
        ]
        result = validate_decision("in_review", "approve", checklist, findings, "reason", "notes", "admin1", "owner1")
        self.assertFalse(result.ok)
        self.assertIn("critical", result.errors[0].lower())
        self.assertIn("acknowledged", result.errors[0].lower())

    def test_approve_critical_finding_with_note_ok(self):
        """Approve allows critical finding if acknowledged with note."""
        checklist = [
            self._make_checklist_item("owner_name_matched", True, True, "ok"),
            self._make_checklist_item("survey_number_matched", True, True, "critical mismatch acknowledged"),
        ]
        findings = [
            self._make_finding("survey_number_matched", "consistency", "critical", "mismatch"),
        ]
        result = validate_decision("in_review", "approve", checklist, findings, "reason", "notes", "admin1", "owner1")
        self.assertTrue(result.ok)
        self.assertEqual(result.new_status, "approved")

    def test_not_applicable_requires_note(self):
        """Not-applicable items need a note for approve."""
        checklist = [
            self._make_checklist_item("owner_name_matched", True, True, "ok"),
            self._make_checklist_item("survey_number_matched", False, False, ""),  # not applicable, no note
        ]
        findings = []
        result = validate_decision("in_review", "approve", checklist, findings, "reason", "notes", "admin1", "owner1")
        self.assertFalse(result.ok)
        self.assertIn("not applicable", result.errors[0].lower())
        self.assertIn("note", result.errors[0].lower())

    def test_not_applicable_with_note_ok(self):
        """Not-applicable with note is allowed."""
        checklist = [
            self._make_checklist_item("owner_name_matched", True, True, "ok"),
            self._make_checklist_item("survey_number_matched", False, False, "no survey doc"),
        ]
        findings = []
        result = validate_decision("in_review", "approve", checklist, findings, "reason", "notes", "admin1", "owner1")
        self.assertTrue(result.ok)
        self.assertEqual(result.new_status, "approved")

    def test_approve_returns_approved_status(self):
        """Approve returns new_status='approved'."""
        checklist = [self._make_checklist_item("owner_name_matched", True, True, "ok")]
        findings = []
        result = validate_decision("in_review", "approve", checklist, findings, "reason", "notes", "admin1", "owner1")
        self.assertTrue(result.ok)
        self.assertEqual(result.new_status, "approved")

    def test_reject_returns_rejected_status(self):
        """Reject returns new_status='rejected'."""
        checklist = [self._make_checklist_item("owner_name_matched", True, True, "ok")]
        findings = []
        result = validate_decision("in_review", "reject", checklist, findings, "reason", "notes", "admin1", "owner1")
        self.assertTrue(result.ok)
        self.assertEqual(result.new_status, "rejected")

    def test_never_auto_approve_or_reject(self):
        """No automatic approval/rejection - only admin action produces status."""
        checklist = []
        findings = []
        result = validate_decision("flagged_for_review", "approve", checklist, findings, "reason", "notes", "admin1", "owner1")
        self.assertFalse(result.ok)
        self.assertIsNone(result.new_status)


class TestRevertOnReupload(unittest.TestCase):

    def test_approved_goes_to_pending(self):
        """Approved listing goes back to pending on re-upload."""
        result = revert_on_reupload("approved")
        self.assertEqual(result, "pending")

    def test_pending_unchanged(self):
        """Pending listing unchanged."""
        result = revert_on_reupload("pending")
        self.assertEqual(result, "pending")

    def test_flagged_for_review_unchanged(self):
        """Flagged for review unchanged."""
        result = revert_on_reupload("flagged_for_review")
        self.assertEqual(result, "flagged_for_review")

    def test_in_review_unchanged(self):
        """In review unchanged."""
        result = revert_on_reupload("in_review")
        self.assertEqual(result, "in_review")

    def test_rejected_unchanged(self):
        """Rejected unchanged."""
        result = revert_on_reupload("rejected")
        self.assertEqual(result, "rejected")


if __name__ == "__main__":
    unittest.main()