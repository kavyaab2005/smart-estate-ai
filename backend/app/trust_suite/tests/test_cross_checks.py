"""
Unit tests for cross_checks.py - pure functions, no database needed.
"""
import pytest
from uuid import uuid4
from app.trust_suite.services.cross_checks import run_cross_checks, cross_check_findings_to_schema, CrossCheckFinding


class TestRunCrossChecks:
    """Tests for run_cross_checks function."""

    def _make_field(self, field_name: str, value: str, doc_type: str = "sale_deed", page: int = 1) -> dict:
        return {
            "field_name": field_name,
            "raw_value": value,
            "normalized_value": value,
            "page_number": page,
            "extraction_method": "text_layer",
            "document_id": str(uuid4()),
            "document_type": doc_type,
        }

    def test_empty_fields_returns_empty(self):
        """Empty extracted fields returns empty findings list."""
        result = run_cross_checks([])
        assert result == []

    def test_owner_name_match(self):
        """Matching owner names produces matched finding."""
        fields = [
            self._make_field("owner_name", "Ramesh Kumar", "sale_deed"),
            self._make_field("owner_name", "Ramesh Kumar", "ec"),
        ]
        result = run_cross_checks(fields)
        owner_findings = [f for f in result if f.check_id == "owner_name_matched"]
        assert len(owner_findings) == 1
        assert owner_findings[0].status == "matched"
        assert owner_findings[0].category == "consistency"
        assert owner_findings[0].severity == "info"

    def test_owner_name_mismatch_critical(self):
        """Mismatched owner names produces critical finding."""
        fields = [
            self._make_field("owner_name", "Ramesh Kumar", "sale_deed"),
            self._make_field("owner_name", "Suresh Patel", "ec"),
        ]
        result = run_cross_checks(fields)
        owner_findings = [f for f in result if f.check_id == "owner_name_matched"]
        assert len(owner_findings) == 1
        assert owner_findings[0].status == "mismatch"
        assert owner_findings[0].severity == "critical"
        assert "mismatch" in owner_findings[0].seller_message.lower()

    def test_owner_name_needs_manual(self):
        """Similar owner names produces needs_manual_verification."""
        fields = [
            self._make_field("owner_name", "R. Kumar", "sale_deed"),
            self._make_field("owner_name", "Ramesh Kumar", "ec"),
        ]
        result = run_cross_checks(fields)
        owner_findings = [f for f in result if f.check_id == "owner_name_matched"]
        assert len(owner_findings) == 1
        assert owner_findings[0].status == "needs_manual_verification"
        assert owner_findings[0].severity == "warning"

    def test_survey_number_match(self):
        """Matching survey numbers produces matched finding."""
        fields = [
            self._make_field("survey_number", "45/2", "sale_deed"),
            self._make_field("survey_no", "45/2", "ec"),
        ]
        result = run_cross_checks(fields)
        survey_findings = [f for f in result if f.check_id == "survey_number_matched"]
        assert len(survey_findings) == 1
        assert survey_findings[0].status == "matched"
        assert survey_findings[0].severity == "info"

    def test_survey_number_mismatch_critical(self):
        """Mismatched survey numbers produces critical finding."""
        fields = [
            self._make_field("survey_number", "45/2", "sale_deed"),
            self._make_field("survey_number", "46/3", "ec"),
        ]
        result = run_cross_checks(fields)
        survey_findings = [f for f in result if f.check_id == "survey_number_matched"]
        assert len(survey_findings) == 1
        assert survey_findings[0].status == "mismatch"
        assert survey_findings[0].severity == "critical"

    def test_area_match_within_tolerance(self):
        """Areas within 5% tolerance produces matched finding."""
        fields = [
            self._make_field("area", "1000 sqft", "sale_deed"),
            self._make_field("area", "1020 sqft", "ec"),
        ]
        result = run_cross_checks(fields)
        area_findings = [f for f in result if f.check_id == "area_matched"]
        assert len(area_findings) == 1
        assert area_findings[0].status == "matched"
        assert area_findings[0].severity == "info"

    def test_area_mismatch_critical(self):
        """Areas outside 5% tolerance produces critical finding."""
        fields = [
            self._make_field("area", "1000 sqft", "sale_deed"),
            self._make_field("area", "1100 sqft", "ec"),
        ]
        result = run_cross_checks(fields)
        area_findings = [f for f in result if f.check_id == "area_matched"]
        assert len(area_findings) == 1
        assert area_findings[0].status == "mismatch"
        assert area_findings[0].severity == "critical"

    def test_registration_number_match(self):
        """Matching registration numbers produces matched finding."""
        fields = [
            self._make_field("registration_number", "REG/2023/1234", "sale_deed"),
            self._make_field("registration_no", "REG/2023/1234", "ec"),
        ]
        result = run_cross_checks(fields)
        reg_findings = [f for f in result if f.check_id == "registration_details_checked"]
        assert len(reg_findings) == 1
        assert reg_findings[0].status == "matched"
        assert reg_findings[0].severity == "info"

    def test_registration_number_mismatch_warning(self):
        """Mismatched registration numbers produces warning finding."""
        fields = [
            self._make_field("registration_number", "REG/2023/1234", "sale_deed"),
            self._make_field("registration_number", "REG/2023/5678", "ec"),
        ]
        result = run_cross_checks(fields)
        reg_findings = [f for f in result if f.check_id == "registration_details_checked"]
        assert len(reg_findings) == 1
        assert reg_findings[0].status == "mismatch"
        assert reg_findings[0].severity == "warning"

    def test_date_match(self):
        """Matching dates produces matched finding."""
        fields = [
            self._make_field("registration_date", "15/08/2023", "sale_deed"),
            self._make_field("execution_date", "15/08/2023", "ec"),
        ]
        result = run_cross_checks(fields)
        date_findings = [f for f in result if f.check_id == "registration_date_matched"]
        assert len(date_findings) == 1
        assert date_findings[0].status == "matched"

    def test_missing_sale_deed_completeness_critical(self):
        """Missing sale deed produces critical completeness finding."""
        fields = [
            self._make_field("owner_name", "Ramesh Kumar", "ec"),
        ]
        result = run_cross_checks(fields)
        missing = [f for f in result if f.check_id == "missing_sale_deed"]
        assert len(missing) == 1
        assert missing[0].category == "completeness"
        assert missing[0].severity == "critical"
        assert "sale deed" in missing[0].seller_message.lower()

    def test_missing_ec_completeness_critical(self):
        """Missing EC produces critical completeness finding."""
        fields = [
            self._make_field("owner_name", "Ramesh Kumar", "sale_deed"),
        ]
        result = run_cross_checks(fields)
        missing = [f for f in result if f.check_id == "missing_ec"]
        assert len(missing) == 1
        assert missing[0].category == "completeness"
        assert missing[0].severity == "critical"
        assert "encumbrance" in missing[0].seller_message.lower() or "ec" in missing[0].seller_message.lower()

    def test_integrity_missing_page_warning(self):
        """Missing page warning produces integrity finding for admin only."""
        fields = [
            self._make_field("owner_name", "Ramesh Kumar", "sale_deed"),
        ]
        # Add warning to field
        fields[0]["warnings"] = ["missing_page_detected: page 2"]
        result = run_cross_checks(fields)
        integrity = [f for f in result if f.check_id == "missing_page"]
        assert len(integrity) == 1
        assert integrity[0].category == "integrity"
        assert integrity[0].severity == "warning"
        assert integrity[0].seller_message is None  # Admin only

    def test_integrity_scan_quality_info(self):
        """Scan quality warning produces integrity finding for admin only."""
        fields = [
            self._make_field("owner_name", "Ramesh Kumar", "sale_deed"),
        ]
        fields[0]["warnings"] = ["scan_quality_low: blurry"]
        result = run_cross_checks(fields)
        integrity = [f for f in result if f.check_id == "scan_quality"]
        assert len(integrity) == 1
        assert integrity[0].category == "integrity"
        assert integrity[0].severity == "info"
        assert integrity[0].seller_message is None  # Admin only

    def test_integrity_wording_never_forged_fraud(self):
        """Integrity findings never use 'forged' or 'fraud' wording."""
        fields = [
            self._make_field("owner_name", "Ramesh Kumar", "sale_deed"),
        ]
        fields[0]["warnings"] = ["missing_page_detected", "scan_quality_low"]
        result = run_cross_checks(fields)
        integrity_findings = [f for f in result if f.category == "integrity"]
        for f in integrity_findings:
            why_raised = f.why_raised.lower()
            assert "forged" not in why_raised
            assert "fraud" not in why_raised
            # Should use recommended wording
            assert "possible indicators" in f.next_step.lower() or "manual review" in f.next_step.lower()

    def test_evidence_includes_document_info(self):
        """Findings include evidence with document info."""
        fields = [
            self._make_field("owner_name", "Ramesh Kumar", "sale_deed"),
            self._make_field("owner_name", "Ramesh Kumar", "ec"),
        ]
        result = run_cross_checks(fields)
        owner_findings = [f for f in result if f.check_id == "owner_name_matched"]
        assert len(owner_findings[0].evidence) >= 2
        for ev in owner_findings[0].evidence:
            assert ev.document_type in ("sale_deed", "ec")
            assert ev.field == "owner_name"


class TestCrossCheckFindingsToSchema:
    """Tests for cross_check_findings_to_schema conversion."""

    def test_conversion_preserves_all_fields(self):
        """Conversion to TrustFindingSchema preserves all fields."""
        finding = CrossCheckFinding(
            check_id="test_check",
            category="consistency",
            severity="critical",
            status="mismatch",
            field="test_field",
            evidence=[],
            why_raised="Test reason",
            next_step="Test next step",
            seller_message="Test seller message",
        )
        schemas = cross_check_findings_to_schema([finding])
        assert len(schemas) == 1
        schema = schemas[0]
        assert schema.check_id == "test_check"
        assert schema.category == "consistency"
        assert schema.severity == "critical"
        assert schema.status == "mismatch"
        assert schema.field == "test_field"
        assert schema.why_raised == "Test reason"
        assert schema.next_step == "Test next step"
        assert schema.seller_message == "Test seller message"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])