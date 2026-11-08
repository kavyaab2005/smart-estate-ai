from enum import Enum
from typing import Optional


class DocType(str, Enum):
    SALE_DEED = "sale_deed"
    EC = "ec"
    KHATA = "khata"
    RTC = "rtc"
    TAX_RECEIPT = "tax_receipt"
    OTHER = "other"


class UnsupportedDocumentType(Exception):
    """Raised when an identity document type is encountered that should not be processed."""
    pass


_ID_MAP = {
    "sale_deed": DocType.SALE_DEED,
    "title_deed": DocType.SALE_DEED,
    "encumbrance_certificate": DocType.EC,
    "ec": DocType.EC,
    "khata": DocType.KHATA,
    "khata_certificate": DocType.KHATA,
    "khata_extract": DocType.KHATA,
    "property_tax_receipt": DocType.TAX_RECEIPT,
    "tax_receipt": DocType.TAX_RECEIPT,
    "rtc": DocType.RTC,
    "pahani": DocType.RTC,
    "record_of_rights": DocType.RTC,
    "tenancy_and_crops": DocType.RTC,
    "approved_plan": DocType.OTHER,
    "other": DocType.OTHER,
    "unknown": DocType.OTHER,
}

_ID_DOC_TYPES = {
    "seller_id",
    "aadhaar",
    "pan",
    "voter",
    "passport",
    "driving_licence",
    "driving_license",
    "identity_proof",
    "id_proof",
}


def normalize_doc_type(raw: Optional[str]) -> DocType:
    """
    Map a raw document type string to a canonical DocType.
    Raises UnsupportedDocumentType for identity document types.
    """
    if not raw:
        return DocType.OTHER

    key = raw.strip().lower().replace(" ", "_").replace("-", "_")

    if key in _ID_DOC_TYPES:
        raise UnsupportedDocumentType(
            f"Document type '{raw}' is an identity document and cannot be processed by trust suite"
        )

    return _ID_MAP.get(key, DocType.OTHER)


def detect_rtc(text: str) -> bool:
    """
    Keyword detection for RTC/Pahani/Record of Rights documents.
    Checks first 15 lines for characteristic terms.
    """
    if not text:
        return False

    lines = [ln.strip().lower() for ln in text.splitlines() if ln.strip()][:15]
    content = "\n".join(lines)

    rtc_keywords = [
        "rtc",
        "pahani",
        "record of rights",
        "tenancy and crops",
        "revenue record",
        "khatedar",
        "survey no",
        "hissa no",
        "extent",
        "revenue department",
    ]

    return any(kw in content for kw in rtc_keywords)
