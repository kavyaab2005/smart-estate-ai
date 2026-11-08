import unittest
from uuid import uuid4
from app.trust_suite.schemas import TrustFindingSchema, FindingEvidence
from app.trust_suite.services.seller_view import to_seller_view, SellerViewOutput, SellerViewFinding


class TestSellerView(unittest.TestCase):

    def _make_finding(
        self,
        check_id: str,
        category: str,
        severity: str,
        status: str,
        field: str = None,
        seller_message: str = None,
        document_type: str = None,
        why_raised: str = "internal reason"
    ) -> TrustFindingSchema:
        evidence = []
        if document_type:
            evidence.append(FindingEvidence(
                document_id=uuid4(),
                document_type=document_type,
                page=1,
                field=field or "",
                raw_value="test",
                normalized_value="test",
            ))
        return TrustFindingSchema(
            check_id=check_id,
            category=category,
            severity=severity,
            status=status,
            field=field,
            evidence=evidence,
            why_raised=why_raised,
            next_step="internal next step",
            seller_message=seller_message,
        )

    def test_returns_only_allowed_fields(self):
        """Output contains only allowed fields: review_status, findings, missing_documents, decision."""
        set_data = {"review_status": "in_review"}
        findings = [
            self._make_finding("owner_name", "consistency", "info", "matched", "owner_name", document_type="sale_deed"),
        ]
        missing = ["encumbrance_certificate"]
        result = to_seller_view(set_data, findings, missing, None)
        self.assertIsInstance(result, SellerViewOutput)
        self.assertEqual(result.review_status, "in_review")
        self.assertEqual(len(result.findings), 1)
        self.assertEqual(result.missing_documents, ["encumbrance_certificate"])
        self.assertIsNone(result.decision)

    def test_findings_include_only_allowed_fields(self):
        """Each finding includes only category, status, document_type, seller_message."""
        set_data = {"review_status": "in_review"}
        findings = [
            self._make_finding("owner_name", "consistency", "info", "matched", "owner_name", document_type="sale_deed"),
        ]
        result = to_seller_view(set_data, findings, [], None)
        finding = result.findings[0]
        self.assertEqual(finding.category, "consistency")
        self.assertEqual(finding.status, "matched")
        self.assertEqual(finding.document_type, "sale_deed")
        self.assertIsInstance(finding.seller_message, str)
        self.assertNotIn("check_id", finding.__dict__)
        self.assertNotIn("evidence", finding.__dict__)
        self.assertNotIn("severity", finding.__dict__)
        self.assertNotIn("field", finding.__dict__)

    def test_never_includes_check_id(self):
        """Output never includes check_id."""
        set_data = {"review_status": "in_review"}
        findings = [
            self._make_finding("owner_name", "consistency", "info", "matched", "owner_name"),
        ]
        result = to_seller_view(set_data, findings, [], None)
        output_str = str(result)
        self.assertNotIn("check_id", output_str)
        self.assertNotIn("owner_name", output_str)

    def test_never_includes_evidence(self):
        """Output never includes evidence details."""
        set_data = {"review_status": "in_review"}
        findings = [
            self._make_finding("owner_name", "consistency", "info", "matched", "owner_name", document_type="sale_deed"),
        ]
        result = to_seller_view(set_data, findings, [], None)
        output_str = str(result)
        self.assertNotIn("evidence", output_str)
        self.assertNotIn("document_id", output_str)
        self.assertNotIn("page", output_str)
        self.assertNotIn("raw_value", output_str)
        self.assertNotIn("normalized_value", output_str)

    def test_never_includes_thresholds(self):
        """Output never includes thresholds."""
        set_data = {"review_status": "in_review"}
        findings = [
            self._make_finding("owner_name", "consistency", "info", "matched", "owner_name"),
        ]
        result = to_seller_view(set_data, findings, [], None)
        output_str = str(result)
        self.assertNotIn("threshold", output_str.lower())

    def test_never_includes_forged_or_fraud(self):
        """Integrity checks worded as 'possible indicators - manual review recommended', never 'forged' or 'fraud'."""
        set_data = {"review_status": "in_review"}
        findings = [
            self._make_finding("missing_page", "integrity", "warning", "needs_manual_verification", "page_2"),
            self._make_finding("scan_quality", "integrity", "info", "needs_manual_verification", "scan"),
        ]
        result = to_seller_view(set_data, findings, [], None)
        output_str = str(result).lower()
        self.assertNotIn("forged", output_str)
        self.assertNotIn("fraud", output_str)
        for finding in result.findings:
            if finding.category == "integrity":
                self.assertEqual(finding.seller_message, "possible indicators - manual review recommended")

    def test_never_includes_internal_notes(self):
        """Output never includes internal notes (why_raised, next_step)."""
        set_data = {"review_status": "in_review"}
        findings = [
            self._make_finding("owner_name", "consistency", "info", "matched", "owner_name"),
        ]
        result = to_seller_view(set_data, findings, [], None)
        output_str = str(result)
        self.assertNotIn("why_raised", output_str)
        self.assertNotIn("next_step", output_str)

    def test_never_includes_score_formula(self):
        """Output never includes score formula."""
        set_data = {"review_status": "in_review"}
        findings = [
            self._make_finding("owner_name", "consistency", "info", "matched", "owner_name"),
        ]
        result = to_seller_view(set_data, findings, [], None)
        output_str = str(result)
        self.assertNotIn("score", output_str.lower())
        self.assertNotIn("percentage", output_str.lower())
        self.assertNotIn("automated", output_str.lower())
        self.assertNotIn("admin_checks", output_str.lower())

    def test_aadhaar_masked_in_seller_message(self):
        """Aadhaar numbers masked in seller_message."""
        set_data = {"review_status": "in_review"}
        findings = [
            self._make_finding("owner_name", "consistency", "info", "mismatch", "owner_name",
                seller_message="Owner Aadhaar 123456789012 does not match"),
        ]
        result = to_seller_view(set_data, findings, [], None)
        self.assertIn("XXXX-XXXX-9012", result.findings[0].seller_message)
        self.assertNotIn("123456789012", result.findings[0].seller_message)

    def test_pan_masked_in_seller_message(self):
        """PAN numbers masked in seller_message."""
        set_data = {"review_status": "in_review"}
        findings = [
            self._make_finding("owner_name", "consistency", "info", "mismatch", "owner_name",
                seller_message="Owner PAN ABCDE1234F does not match"),
        ]
        result = to_seller_view(set_data, findings, [], None)
        self.assertIn("XXXXX1234X", result.findings[0].seller_message)
        self.assertNotIn("ABCDE1234F", result.findings[0].seller_message)

    def test_rejection_reason_masked_and_included(self):
        """Rejection reason masked and included in decision."""
        set_data = {"review_status": "rejected"}
        findings = []
        decision = {"action": "reject", "reason": "Aadhaar 123456789012 mismatch"}
        result = to_seller_view(set_data, findings, [], decision)
        self.assertIsNotNone(result.decision)
        self.assertEqual(result.decision.action, "rejected")
        self.assertIn("XXXX-XXXX-9012", result.decision.reason)
        self.assertNotIn("123456789012", result.decision.reason)

    def test_approval_summary_masked_and_included(self):
        """Approval summary masked and included in decision."""
        set_data = {"review_status": "approved"}
        findings = []
        decision = {"action": "approve", "notes": "Approved with PAN ABCDE1234F verified"}
        result = to_seller_view(set_data, findings, [], decision)
        self.assertIsNotNone(result.decision)
        self.assertEqual(result.decision.action, "approved")
        self.assertIn("XXXXX1234X", result.decision.summary)
        self.assertNotIn("ABCDE1234F", result.decision.summary)

    def test_consistency_mismatch_message(self):
        """Consistency mismatch gets appropriate seller message."""
        set_data = {"review_status": "in_review"}
        findings = [
            self._make_finding("survey_number", "consistency", "warning", "mismatch", "survey_number"),
        ]
        result = to_seller_view(set_data, findings, [], None)
        self.assertIn("Mismatch detected", result.findings[0].seller_message)
        self.assertIn("survey_number", result.findings[0].seller_message)

    def test_consistency_needs_manual_verification_message(self):
        """Consistency needs_manual_verification gets appropriate seller message."""
        set_data = {"review_status": "in_review"}
        findings = [
            self._make_finding("area", "consistency", "info", "needs_manual_verification", "area"),
        ]
        result = to_seller_view(set_data, findings, [], None)
        self.assertIn("Manual verification needed", result.findings[0].seller_message)
        self.assertIn("area", result.findings[0].seller_message)

    def test_consistency_matched_message(self):
        """Consistency matched gets appropriate seller message."""
        set_data = {"review_status": "in_review"}
        findings = [
            self._make_finding("owner_name", "consistency", "info", "matched", "owner_name"),
        ]
        result = to_seller_view(set_data, findings, [], None)
        self.assertEqual(result.findings[0].seller_message, "Matched across documents")

    def test_completeness_message(self):
        """Completeness finding gets appropriate seller message."""
        set_data = {"review_status": "in_review"}
        findings = [
            self._make_finding("missing_doc", "completeness", "warning", "needs_manual_verification", "doc",
                why_raised="Document missing"),
        ]
        result = to_seller_view(set_data, findings, [], None)
        self.assertIn("Document completeness issue", result.findings[0].seller_message)
        self.assertIn("Document missing", result.findings[0].seller_message)

    def test_custom_seller_message_used_when_provided(self):
        """Custom seller_message from finding is used and masked."""
        set_data = {"review_status": "in_review"}
        findings = [
            self._make_finding("owner_name", "consistency", "info", "mismatch", "owner_name",
                seller_message="Owner name mismatch: Aadhaar 123456789012"),
        ]
        result = to_seller_view(set_data, findings, [], None)
        self.assertIn("XXXX-XXXX-9012", result.findings[0].seller_message)
        self.assertNotIn("123456789012", result.findings[0].seller_message)

    def test_missing_documents_included(self):
        """Missing documents list included in output."""
        set_data = {"review_status": "in_review"}
        findings = []
        missing = ["encumbrance_certificate", "tax_receipt"]
        result = to_seller_view(set_data, findings, missing, None)
        self.assertEqual(result.missing_documents, ["encumbrance_certificate", "tax_receipt"])

    def test_empty_findings_handled(self):
        """Empty findings list handled correctly."""
        set_data = {"review_status": "in_review"}
        findings = []
        missing = []
        result = to_seller_view(set_data, findings, missing, None)
        self.assertEqual(result.findings, [])
        self.assertEqual(result.missing_documents, [])

    def test_no_decision_when_none_provided(self):
        """No decision in output when none provided."""
        set_data = {"review_status": "in_review"}
        findings = [
            self._make_finding("owner_name", "consistency", "info", "matched", "owner_name"),
        ]
        result = to_seller_view(set_data, findings, [], None)
        self.assertIsNone(result.decision)


if __name__ == "__main__":
    unittest.main()