from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from uuid import uuid4

from app.trust_suite.schemas import TrustFindingSchema, FindingEvidence, mask_identifiers
from app.trust_suite.services.normalize import (
    normalize_name,
    names_match,
    normalize_survey_number,
    parse_date,
    to_sqft,
    areas_match,
)


@dataclass
class CrossCheckFinding:
    check_id: str
    category: str
    severity: str
    status: str
    field: Optional[str]
    evidence: List[FindingEvidence]
    why_raised: str
    next_step: str
    seller_message: Optional[str]


def _group_fields_by_name(extracted_fields: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group extracted fields by field_name."""
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for field in extracted_fields:
        field_name = field.get("field_name")
        if field_name:
            grouped.setdefault(field_name, []).append(field)
    return grouped


def _get_all_field_values(grouped: Dict[str, List[Dict[str, Any]]], field_names: List[str]) -> List[str]:
    """Get all non-empty values for a list of field names across all documents."""
    values = []
    for field_name in field_names:
        fields = grouped.get(field_name, [])
        for field in fields:
            value = field.get("normalized_value") or field.get("raw_value")
            if value and value.strip():
                values.append(str(value))
    return values


def _create_evidence(fields: List[Dict[str, Any]], field_name: str) -> List[FindingEvidence]:
    """Create FindingEvidence objects from extracted fields."""
    evidence = []
    for field in fields:
        if field.get("field_name") == field_name:
            evidence.append(FindingEvidence(
                document_id=field.get("document_id", uuid4()),
                document_type=field.get("document_type", "unknown"),
                page=field.get("page_number", 1),
                field=field_name,
                raw_value=mask_identifiers(str(field.get("raw_value", ""))),
                normalized_value=mask_identifiers(str(field.get("normalized_value", ""))),
            ))
    return evidence


def run_cross_checks(
    extracted_fields: List[Dict[str, Any]],
    property_data: Optional[Dict[str, Any]] = None
) -> List[CrossCheckFinding]:
    """
    Run cross-document consistency checks on extracted fields.

    Compares owner name, survey number, area, and registration details across documents.
    Returns findings with severity, seller_message in plain language, and internal evidence.
    Integrity indicators are findings for admin only with wording "possible indicators - manual review recommended".
    """
    if not extracted_fields:
        return []

    grouped = _group_fields_by_name(extracted_fields)
    findings = []

    # 1. Owner name consistency check
    owner_names = _get_all_field_values(grouped, ["owner_name", "seller_name", "name"])

    if len(owner_names) >= 2:
        status, score = names_match(owner_names[0], owner_names[1])
        severity = "critical" if status == "mismatch" else ("warning" if status == "needs_manual_verification" else "info")
        evidence = _create_evidence(grouped.get("owner_name", []) + grouped.get("seller_name", []) + grouped.get("name", []), "owner_name")
        masked_name_0 = mask_identifiers(owner_names[0])
        masked_name_1 = mask_identifiers(owner_names[1])
        findings.append(CrossCheckFinding(
            check_id="owner_name_matched",
            category="consistency",
            severity=severity,
            status=status,
            field="owner_name",
            evidence=evidence,
            why_raised=f"Owner name comparison: '{masked_name_0}' vs '{masked_name_1}' (score: {score:.1f})",
            next_step="Admin to verify owner identity across documents",
            seller_message="Owner name mismatch detected across documents" if status == "mismatch"
                        else "Manual verification needed for owner name" if status == "needs_manual_verification"
                        else None,
        ))

    # 2. Survey number consistency check
    survey_numbers = []
    for field_name in ["survey_number", "survey_no", "sy_no", "site_no"]:
        values = _get_all_field_values(grouped, [field_name])
        for v in values:
            survey_numbers.append(normalize_survey_number(v))

    if len(survey_numbers) >= 2:
        match = survey_numbers[0] == survey_numbers[1]
        status = "matched" if match else "mismatch"
        severity = "critical" if not match else "info"
        evidence = _create_evidence(grouped.get("survey_number", []) + grouped.get("survey_no", []) + grouped.get("sy_no", []) + grouped.get("site_no", []), "survey_number")
        masked_sn_0 = mask_identifiers(survey_numbers[0])
        masked_sn_1 = mask_identifiers(survey_numbers[1])
        findings.append(CrossCheckFinding(
            check_id="survey_number_matched",
            category="consistency",
            severity=severity,
            status=status,
            field="survey_number",
            evidence=evidence,
            why_raised=f"Survey number comparison: '{masked_sn_0}' vs '{masked_sn_1}'",
            next_step="Admin to verify survey number consistency" if not match else "Verified automatically",
            seller_message="Survey number mismatch detected across documents" if not match else None,
        ))

    # 3. Area consistency check
    area_values = []
    for field_name in ["area", "area_sqft", "total_area", "built_up_area", "carpet_area"]:
        values = _get_all_field_values(grouped, [field_name])
        for value in values:
            # Try to extract number and unit
            import re
            match = re.search(r"([\d,]+\.?\d*)\s*(\w+)?", value.replace(",", ""))
            if match:
                num = float(match.group(1))
                unit = match.group(2) or "sqft"
                area_values.append((num, unit))

    if len(area_values) >= 2:
        a_sqft = to_sqft(area_values[0][0], area_values[0][1])
        b_sqft = to_sqft(area_values[1][0], area_values[1][1])
        match, diff_pct = areas_match(a_sqft, b_sqft)
        status = "matched" if match else "mismatch"
        severity = "critical" if not match else "info"
        evidence = _create_evidence(grouped.get("area", []) + grouped.get("area_sqft", []) + grouped.get("total_area", []) + grouped.get("built_up_area", []) + grouped.get("carpet_area", []), "area")
        findings.append(CrossCheckFinding(
            check_id="area_matched",
            category="consistency",
            severity=severity,
            status=status,
            field="area",
            evidence=evidence,
            why_raised=f"Area comparison: {a_sqft:.0f} sqft vs {b_sqft:.0f} sqft (diff: {diff_pct:.1f}%)",
            next_step="Admin to verify area measurements" if not match else "Verified automatically",
            seller_message="Area measurements mismatch across documents" if not match else None,
        ))

    # 4. Registration details consistency check (registration number, date)
    reg_numbers = _get_all_field_values(grouped, ["registration_number", "registration_no", "reg_number", "doc_number"])

    if len(reg_numbers) >= 2:
        match = reg_numbers[0] == reg_numbers[1]
        status = "matched" if match else "mismatch"
        severity = "warning" if not match else "info"
        evidence = _create_evidence(grouped.get("registration_number", []) + grouped.get("registration_no", []) + grouped.get("reg_number", []) + grouped.get("doc_number", []), "registration_number")
        masked_reg_0 = mask_identifiers(reg_numbers[0])
        masked_reg_1 = mask_identifiers(reg_numbers[1])
        findings.append(CrossCheckFinding(
            check_id="registration_details_checked",
            category="consistency",
            severity=severity,
            status=status,
            field="registration_number",
            evidence=evidence,
            why_raised=f"Registration number comparison: '{masked_reg_0}' vs '{masked_reg_1}'",
            next_step="Admin to verify registration details",
            seller_message="Registration details mismatch detected across documents" if not match else None,
        ))

    # 5. Date consistency check (registration date, execution date)
    dates = []
    for field_name in ["registration_date", "execution_date", "date_of_registration", "date"]:
        values = _get_all_field_values(grouped, [field_name])
        for value in values:
            parsed = parse_date(value)
            if parsed:
                dates.append((field_name, parsed, value))

    if len(dates) >= 2:
        # Check if dates match
        match = dates[0][1] == dates[1][1]
        status = "matched" if match else "mismatch"
        severity = "warning" if not match else "info"
        evidence = _create_evidence(grouped.get("registration_date", []) + grouped.get("execution_date", []) + grouped.get("date_of_registration", []) + grouped.get("date", []), "registration_date")
        masked_date_0 = mask_identifiers(dates[0][2])
        masked_date_1 = mask_identifiers(dates[1][2])
        findings.append(CrossCheckFinding(
            check_id="registration_date_matched",
            category="consistency",
            severity=severity,
            status=status,
            field="registration_date",
            evidence=evidence,
            why_raised=f"Date comparison: '{masked_date_0}' vs '{masked_date_1}'",
            next_step="Admin to verify registration date consistency",
            seller_message="Registration dates mismatch across documents" if not match else None,
        ))

    # 6. Integrity indicators - check for missing pages, scan quality issues
    # These are findings for admin only - wording per SCORE_RULES.md Rule 4
    for field_data in extracted_fields:
        warnings = field_data.get("warnings", [])
        for warning in warnings:
            if "missing_page" in warning.lower() or "page_missing" in warning.lower():
                findings.append(CrossCheckFinding(
                    check_id="missing_page",
                    category="integrity",
                    severity="warning",
                    status="needs_manual_verification",
                    field="page",
                    evidence=[FindingEvidence(
                        document_id=field_data.get("document_id", uuid4()),
                        document_type=field_data.get("document_type", "unknown"),
                        page=field_data.get("page_number", 1),
                        field="page",
                        raw_value="",
                        normalized_value="",
                    )],
                    why_raised=f"Possible missing page detected: {mask_identifiers(warning)}",
                    next_step="possible indicators - manual review recommended",
                    seller_message=None,  # Integrity findings don't go to seller
                ))
            elif "scan_quality" in warning.lower() or "blur" in warning.lower() or "unreadable" in warning.lower():
                findings.append(CrossCheckFinding(
                    check_id="scan_quality",
                    category="integrity",
                    severity="info",
                    status="needs_manual_verification",
                    field="scan_quality",
                    evidence=[FindingEvidence(
                        document_id=field_data.get("document_id", uuid4()),
                        document_type=field_data.get("document_type", "unknown"),
                        page=field_data.get("page_number", 1),
                        field="scan_quality",
                        raw_value="",
                        normalized_value="",
                    )],
                    why_raised=f"Possible scan quality issue: {mask_identifiers(warning)}",
                    next_step="possible indicators - manual review recommended",
                    seller_message=None,
                ))

    # 7. Completeness check - check for required document types
    doc_types_present = set()
    for field_data in extracted_fields:
        doc_type = field_data.get("document_type", "")
        if doc_type:
            doc_types_present.add(doc_type.lower())

    required_types = {"sale_deed", "ec"}
    for req_type in required_types:
        if req_type not in doc_types_present:
            findings.append(CrossCheckFinding(
                check_id=f"missing_{req_type}",
                category="completeness",
                severity="critical",
                status="needs_manual_verification",
                field=req_type,
                evidence=[],
                why_raised=f"Required document type '{req_type}' not found in uploaded documents",
                next_step="Seller to upload missing document",
                seller_message=f"Missing required document: {req_type.replace('_', ' ').title()}",
            ))

    return findings


def cross_check_findings_to_schema(findings: List[CrossCheckFinding]) -> List[TrustFindingSchema]:
    """Convert CrossCheckFinding to TrustFindingSchema for storage."""
    return [
        TrustFindingSchema(
            check_id=f.check_id,
            category=f.category,
            severity=f.severity,
            status=f.status,
            field=f.field,
            evidence=f.evidence,
            why_raised=f.why_raised,
            next_step=f.next_step,
            seller_message=f.seller_message,
        )
        for f in findings
    ]