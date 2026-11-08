from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from app.ocr.field_extractor import extract_fields
from app.trust_suite.schemas import mask_identifiers


@dataclass
class ExtractedField:
    field_name: str
    raw_value: Optional[str]
    normalized_value: Optional[str]
    page_number: int
    extraction_method: str


_PAN_AADHAAR_FIELDS = {"pan_number", "aadhaar_masked"}


def extract_trust_fields(
    pages: List[Dict[str, Any]],
    doc_type_hint: Optional[str] = None
) -> List[ExtractedField]:
    """
    Extract trust-relevant fields from page texts.

    Args:
        pages: List of dicts with keys 'page', 'text', 'method', 'warnings'
        doc_type_hint: Optional document type hint

    Returns:
        List of ExtractedField objects (PAN/Aadhaar fields dropped, values masked)
    """
    results: List[ExtractedField] = []

    for page_data in pages:
        page_num = page_data.get("page", 1)
        text = page_data.get("text", "")
        method = page_data.get("method", "unknown")

        if not text or not text.strip():
            continue

        extracted = extract_fields(text, doc_type=doc_type_hint)

        for field_name, raw_value in extracted.items():
            if field_name in _PAN_AADHAAR_FIELDS:
                continue

            if raw_value is None:
                continue

            masked_raw = mask_identifiers(str(raw_value))
            masked_norm = mask_identifiers(str(raw_value))

            results.append(ExtractedField(
                field_name=field_name,
                raw_value=masked_raw,
                normalized_value=masked_norm,
                page_number=page_num,
                extraction_method=method,
            ))

    return results
