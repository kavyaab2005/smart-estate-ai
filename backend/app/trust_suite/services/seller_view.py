from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from app.trust_suite.schemas import mask_identifiers
@dataclass
class SellerViewFinding:
    category: str
    status: str
    document_type: Optional[str]
    seller_message: str
@dataclass
class SellerViewDecision:
    action: str
    reason: Optional[str] = None
    summary: Optional[str] = None
@dataclass
class SellerViewOutput:
    review_status: str
    findings: List[SellerViewFinding]
    missing_documents: List[str]
    decision: Optional[SellerViewDecision] = None
def _get_field(finding: Any) -> Optional[str]:
    """Field name works for both DB models (field_name) and schemas (field)."""
    return getattr(finding, "field_name", None) or getattr(finding, "field", None)
def _get_document_type(finding: Any) -> Optional[str]:
    """First evidence document type, for DB models (evidence_json) and schemas (evidence)."""
    evidence = getattr(finding, "evidence_json", None)
    if evidence is None:
        evidence = getattr(finding, "evidence", None)
    if not evidence:
        return None
    if isinstance(evidence, dict):
        evidence = [evidence]
    first = evidence[0]
    if isinstance(first, dict):
        return first.get("document_type")
    return getattr(first, "document_type", None)
def _get_seller_message(finding: Any) -> str:
    """Get the seller-facing message for a finding."""
    if finding.seller_message and finding.seller_message.strip():
        return mask_identifiers(finding.seller_message)
    field = _get_field(finding)
    if finding.category == "integrity":
        return "possible indicators - manual review recommended"
    if finding.category == "consistency":
        if finding.status == "mismatch":
            return f"Mismatch detected in {field or 'field'} across documents"
        elif finding.status == "needs_manual_verification":
            return f"Manual verification needed for {field or 'field'}"
        return "Matched across documents"
    if finding.category == "completeness":
        return mask_identifiers(f"Document completeness issue: {finding.why_raised}")
    return mask_identifiers(finding.why_raised or "")
def to_seller_view(
    set_data: Dict[str, Any],
    findings: List[Any],
    missing_documents: List[str],
    decision: Optional[Dict[str, Any]] = None
) -> SellerViewOutput:
    """
    Convert internal review data to seller-facing view.
    Returns ONLY:
    - review status
    - each finding's seller_message text (for consistency/completeness only)
    - missing documents
    - admin's rejection reason or approval summary
    NEVER includes:
    - integrity/forensic indicators
    - evidence details
    - check_ids
    - thresholds
    - internal notes
    - score formula
    Aadhaar/PAN are masked using mask_identifiers.
    Integrity checks are excluded entirely from seller view.
    """
    review_status = set_data.get("review_status", "unknown")
    seller_findings = []
    for finding in findings:
        # Skip integrity findings entirely - they are for admin only
        if finding.category == "integrity":
            continue
        seller_findings.append(SellerViewFinding(
            category=finding.category,
            status=finding.status,
            document_type=_get_document_type(finding),
            seller_message=_get_seller_message(finding),
        ))
    seller_decision = None
    if decision:
        action = decision.get("action")
        if action == "reject":
            seller_decision = SellerViewDecision(
                action="rejected",
                reason=mask_identifiers(decision.get("reason", "")) if decision.get("reason") else None,
            )
        elif action == "approve":
            seller_decision = SellerViewDecision(
                action="approved",
                summary=mask_identifiers(decision.get("notes", "")) if decision.get("notes") else None,
            )
    return SellerViewOutput(
        review_status=review_status,
        findings=seller_findings,
        missing_documents=list(missing_documents),
        decision=seller_decision,
    )