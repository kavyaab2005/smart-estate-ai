from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.trust_suite.schemas import TrustFindingSchema, TrustAdminChecklistItem


SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


@dataclass
class PriorityResult:
    priority: int
    is_flagged: bool


@dataclass
class DecisionResult:
    ok: bool
    errors: List[str]
    new_status: Optional[str] = None


def queue_priority(
    findings: List[TrustFindingSchema],
    missing_documents: List[str]
) -> PriorityResult:
    """
    Compute a sortable priority for the review queue.

    EVERY document set is queued (never skipped).
    Flagged sets (critical > warning > info findings, or missing documents) sort first.
    Clean sets (no findings, no missing documents) are last.

    Returns:
        PriorityResult with priority (lower = higher priority) and is_flagged flag
    """
    has_missing = len(missing_documents) > 0

    if has_missing:
        return PriorityResult(priority=0, is_flagged=True)

    if not findings:
        return PriorityResult(priority=100, is_flagged=False)

    max_severity = min((SEVERITY_ORDER.get(f.severity, 3) for f in findings), default=3)

    if max_severity == 0:
        return PriorityResult(priority=1, is_flagged=True)
    elif max_severity == 1:
        return PriorityResult(priority=2, is_flagged=True)
    elif max_severity == 2:
        return PriorityResult(priority=3, is_flagged=True)

    return PriorityResult(priority=100, is_flagged=False)


def validate_decision(
    current_status: str,
    action: str,
    checklist_items: List[TrustAdminChecklistItem],
    findings: List[TrustFindingSchema],
    reason: Optional[str],
    notes: Optional[str],
    approver_id: str,
    listing_owner_id: str
) -> DecisionResult:
    """
    Validate an admin decision (approve/reject).

    Rules:
    - Only allowed when current_status == "in_review"
    - Approver must NOT be the listing owner
    - Reject requires a non-empty reason
    - Approve requires:
        * Every APPLICABLE checklist item decided (verified, or not verified WITH a note)
        * Every critical finding acknowledged WITH a note
        * Not-applicable items need a note
    - Returns DecisionResult with ok/errors and new status: approve -> "approved", reject -> "rejected"
    """
    errors = []

    if current_status != "in_review":
        errors.append("Decision only allowed when status is 'in_review'")

    if approver_id == listing_owner_id:
        errors.append("Approver cannot be the listing owner")

    if action == "reject":
        if not reason or not reason.strip():
            errors.append("Rejection requires a reason")
    elif action == "approve":
        for item in checklist_items:
            if not item.is_applicable:
                if not item.note or not item.note.strip():
                    errors.append(f"Item '{item.item_key}' marked not applicable without a note")
            else:
                if not item.verified and (not item.note or not item.note.strip()):
                    errors.append(f"Applicable item '{item.item_key}' not verified and no note provided")

        critical_findings = [f for f in findings if f.severity == "critical"]
        for finding in critical_findings:
            matching_item = next(
                (item for item in checklist_items if item.item_key == finding.check_id),
                None
            )
            if matching_item and (not matching_item.note or not matching_item.note.strip()):
                errors.append(f"Critical finding '{finding.check_id}' not acknowledged with a note")

    if errors:
        return DecisionResult(ok=False, errors=errors)

    new_status = "approved" if action == "approve" else "rejected"
    return DecisionResult(ok=True, errors=[], new_status=new_status)


def revert_on_reupload(current_property_status: str) -> str:
    """
    Determine new property status when documents are re-uploaded.

    An "approved" listing goes back to "pending"; others unchanged.
    """
    if current_property_status == "approved":
        return "pending"
    return current_property_status