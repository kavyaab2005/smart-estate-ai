import re
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Document type detection (from the title line at the top of the document)
# ---------------------------------------------------------------------------
DOC_TITLES = [
    ("sale_deed", ["sale deed"]),
    ("khata", ["khata certificate", "khata extract"]),
    ("encumbrance_certificate", ["encumbrance certificate"]),
    ("property_tax_receipt", ["property tax receipt", "tax receipt"]),
    ("seller_id", ["seller identity proof", "identity proof"]),
]

PROPERTY_TYPE_PREFIX = re.compile(
    r"^(independent house|apartment|villa|plot|flat|house)\s*,\s*", re.IGNORECASE
)
MORTGAGE_WORDS = ("mortgage", "lien", "loan", "hypothecat", "charge created")

LABEL_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9 /\-\.\(\)]{1,60}?)\s*:\s*(\S.*)$")


def detect_doc_type(text: str) -> Optional[str]:
    """Guess the document type from the first few lines (the title)."""
    lines = [ln.strip().lower() for ln in text.splitlines() if ln.strip()][:8]
    for line in lines:
        for doc_type, titles in DOC_TITLES:
            if any(t in line for t in titles):
                return doc_type
    return None


def parse_labeled_lines(text: str) -> Dict[str, str]:
    """Turns 'Label: Value' lines into a dict. Keeps the first occurrence of each label."""
    found: Dict[str, str] = {}
    for line in text.splitlines():
        m = LABEL_RE.match(line)
        if not m:
            continue
        key = re.sub(r"\s*\(.*?\)", "", m.group(1)).strip().lower()  # drop "(Fictional)" etc.
        key = re.sub(r"\s+", " ", key)
        found.setdefault(key, m.group(2).strip())
    return found


def _get(labels: Dict[str, str], *names: str) -> Optional[str]:
    for n in names:
        val = labels.get(n)
        if val and val.strip():
            return val.strip()
    return None


# ---------------------------------------------------------------------------
# Fallback patterns, used only when no labelled line is found
# ---------------------------------------------------------------------------
def _fallback_survey(text: str) -> Optional[str]:
    m = re.search(
        r"(?:Survey|Sy|Site)\s*[/\.]?\s*(?:Site)?\s*(?:Number|No)\.?\s*[:\-]?\s*([0-9]+[A-Za-z0-9\/\-]*)",
        text, re.IGNORECASE,
    )
    return m.group(1).strip() if m else None


def _fallback_area(text: str) -> Optional[str]:
    m = re.search(r"\b([0-9][0-9\.,]*\s*(?:sq\.?\s*ft\.?|sqft|square\s*feet))", text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def _fallback_owner(text: str) -> Optional[str]:
    m = re.search(r"(?:Mr\.|Mrs\.|Ms\.|Shri|Smt\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", text)
    return m.group(1).strip() if m else None


def _clean_id(value: Optional[str]) -> Optional[str]:
    """Survey-style identifiers: remove spaces, uppercase."""
    if not value:
        return None
    return re.sub(r"\s+", "", value).upper()


def _digits_only(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    digits = re.sub(r"[^0-9]", "", value)
    return digits or None


def _extract_epid(text: str) -> Optional[str]:
    """ePID = the 10-digit number printed most often (a Khata repeats it on each page)."""
    from collections import Counter
    ids = Counter(re.findall(r"(?<!\d)\d{10}(?!\d)", text))
    top = ids.most_common(2)
    if not top or top[0][1] < 2:
        return None
    if len(top) > 1 and top[1][1] == top[0][1]:
        return None
    return top[0][0]
def extract_fields(raw_text: str, doc_type: Optional[str] = None) -> Dict[str, Optional[str]]:
    """
    Reads 'Label: Value' lines from OCR / PDF text.

    Returns the 7 original fields plus document-specific extras that the
    verification rules need (khata_type, tax_status, encumbrance_found, ...).
    doc_type is optional; if missing it is detected from the title line.
    """
    keys = [
        "owner_name", "property_address", "property_id", "epid", "survey_number", "area",
        "document_date", "registration_number",
        "detected_doc_type", "khata_type", "khata_number", "ec_number", "ec_remarks",
        "encumbrance_found", "tax_status", "financial_year", "amount_paid",
        "sale_consideration", "buyer_name", "pan_number", "aadhaar_masked",
    ]
    if not raw_text or not raw_text.strip():
        return {k: None for k in keys}

    detected = detect_doc_type(raw_text)
    labels = parse_labeled_lines(raw_text)
    lowered = raw_text.lower()

    # --- the 7 original fields ---
    owner = _get(labels, "owner name", "seller name", "name", "owner") or _fallback_owner(raw_text)

    address = _get(labels, "property address", "address")
    if not address:
        desc = _get(labels, "property description")
        if desc:
            address = PROPERTY_TYPE_PREFIX.sub("", desc)

    survey = _clean_id(
        _get(labels, "survey/site number", "survey number", "survey no", "survey/site no", "site number")
        or _fallback_survey(raw_text)
    )

    area = _get(labels, "built-up area", "plot area", "area", "extent") or _fallback_area(raw_text)

    date = _get(labels, "registration date", "issue date", "payment date", "date", "dated")

    # --- extras for document-specific checks ---
    khata_type = None
    raw_kt = _get(labels, "khata type")
    if raw_kt:
        m = re.match(r"\s*([AB])\b", raw_kt, re.IGNORECASE)
        khata_type = m.group(1).upper() if m else raw_kt.upper()

    remarks = _get(labels, "remarks")
    encumbrance_found = None
    effective_doc = doc_type or detected
    if effective_doc == "encumbrance_certificate" or "encumbrance" in lowered[:300]:
        has_mortgage = any(w in lowered for w in MORTGAGE_WORDS)
        clean_remark = bool(remarks) and "no encumbrance" in remarks.lower()
        if has_mortgage:
            encumbrance_found = "true"
        elif clean_remark:
            encumbrance_found = "false"
        elif remarks:
            encumbrance_found = "true"

    tax_status = _get(labels, "status")
    pan = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", raw_text)
    aadhaar = re.search(r"\b(X{4}\s?X{4}\s?[0-9]{4})\b", raw_text)

    return {
        "owner_name": owner,
        "property_address": address,
        "property_id": _get(labels, "property id", "linked property id"),
        "epid": _extract_epid(raw_text),
        "survey_number": survey,
        "area": area,
        "document_date": date,
        "registration_number": _get(labels, "registration number"),
        "detected_doc_type": detected,
        "khata_type": khata_type,
        "khata_number": _get(labels, "khata number"),
        "ec_number": _get(labels, "ec number"),
        "ec_remarks": remarks,
        "encumbrance_found": encumbrance_found,
        "tax_status": tax_status.upper() if tax_status else None,
        "financial_year": _get(labels, "financial year"),
        "amount_paid": _digits_only(_get(labels, "amount paid")),
        "sale_consideration": _digits_only(_get(labels, "sale consideration")),
        "buyer_name": _get(labels, "buyer name"),
        "pan_number": pan.group(1) if pan else None,
        "aadhaar_masked": aadhaar.group(1) if aadhaar else None,
    }