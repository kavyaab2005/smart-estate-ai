from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.trust_suite.schemas import TrustFindingSchema, TrustAdminChecklistItem


DISCLAIMER = "This is a consistency and verification summary, not legal advice or proof of title. Consult an advocate before paying or registering."


@dataclass
class ScoreBreakdown:
    automated_checks_total: int
    automated_checks_passed: int
    admin_checks_total: int
    admin_checks_passed: int
    score_percentage: Dict[str, float]
    breakdown_json: Dict[str, Any]
    display_text: str
    disclaimer: str


def _count_automated(automated_results: List[TrustFindingSchema], missing_documents: List[str]) -> tuple[int, int]:
    """Count automated consistency checks. Missing documents count in total but not passed."""
    consistency_checks = [f for f in automated_results if f.category == "consistency"]
    total = len(consistency_checks)
    passed = len([f for f in consistency_checks if f.status == "matched"])
    return total, passed


def _count_admin(checklist_items: List[TrustAdminChecklistItem]) -> tuple[int, int, List[str]]:
    """Count admin checklist items. Not-applicable items are excluded from both counts.
    Returns (total, passed, errors)."""
    errors = []
    applicable_items = []
    for item in checklist_items:
        if not item.is_applicable:
            if not item.note or not item.note.strip():
                errors.append(f"Checklist item '{item.item_key}' marked not applicable without a note")
            continue
        applicable_items.append(item)

    total = len(applicable_items)
    passed = len([item for item in applicable_items if item.verified])
    return total, passed, errors


def compute_score(
    automated_results: List[TrustFindingSchema],
    checklist_items: List[TrustAdminChecklistItem],
    missing_documents: Optional[List[str]] = None
) -> ScoreBreakdown:
    """
    Compute the trust score breakdown following SCORE_RULES.md.

    Args:
        automated_results: List of automated findings (consistency, integrity, completeness)
        checklist_items: List of admin checklist items with is_applicable and verified status
        missing_documents: Optional list of missing document types

    Returns:
        ScoreBreakdown with automated/admin counts, percentages, display text, and disclaimer
    """
    if missing_documents is None:
        missing_documents = []

    automated_total, automated_passed = _count_automated(automated_results, missing_documents)
    admin_total, admin_passed, errors = _count_admin(checklist_items)

    if errors:
        raise ValueError("; ".join(errors))

    automated_pct = (automated_passed / automated_total * 100.0) if automated_total > 0 else 0.0
    admin_pct = (admin_passed / admin_total * 100.0) if admin_total > 0 else 0.0

    score_percentage = {
        "automated": round(automated_pct, 2),
        "admin": round(admin_pct, 2),
    }

    display_text = f"{admin_passed} of {admin_total} verified"

    breakdown_json = {
        "automated": {
            "total": automated_total,
            "passed": automated_passed,
            "percentage": score_percentage["automated"],
        },
        "admin": {
            "total": admin_total,
            "passed": admin_passed,
            "percentage": score_percentage["admin"],
        },
        "missing_documents": missing_documents,
    }

    return ScoreBreakdown(
        automated_checks_total=automated_total,
        automated_checks_passed=automated_passed,
        admin_checks_total=admin_total,
        admin_checks_passed=admin_passed,
        score_percentage=score_percentage,
        breakdown_json=breakdown_json,
        display_text=display_text,
        disclaimer=DISCLAIMER,
    )