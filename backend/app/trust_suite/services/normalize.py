import re
from datetime import date, datetime
from typing import Optional, Tuple

try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False


_HONORIFICS = re.compile(r"^\s*(mr\.?|mrs\.?|ms\.?|shri|smt\.?|sri|dr\.?|prof\.?)\s+", re.IGNORECASE)
_SO_DO_WO = re.compile(r"\b(s/o|d/o|w/o|c/o)\s+\w+", re.IGNORECASE)
_INITIALS = re.compile(r"\b([A-Z])\.\s*")
_MULTI_SPACE = re.compile(r"\s+")
_PUNCT = re.compile(r"[.,'\"\-]")


def normalize_name(name: str) -> str:
    """
    Normalize a person name for comparison:
    - Remove honorifics (Mr, Mrs, Shri, Smt, etc.)
    - Remove S/o, D/o, W/o, C/o parts
    - Expand initials to single letter (kept as-is)
    - Remove punctuation
    - Collapse whitespace
    - Uppercase
    """
    if not name:
        return ""

    s = name.strip()
    s = _HONORIFICS.sub("", s)
    s = _SO_DO_WO.sub("", s)
    s = _PUNCT.sub(" ", s)
    s = _MULTI_SPACE.sub(" ", s)
    return s.strip().upper()


def _jaccard_similarity(a: str, b: str) -> float:
    """Fallback Jaccard similarity on word tokens."""
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def names_match(a: str, b: str) -> Tuple[str, float]:
    """
    Compare two names and return (status, score).
    status: "matched" | "needs_manual_verification" | "mismatch"
    score: 0.0 to 100.0

    New rule: "matched" ONLY if both names have exactly the same set of word tokens (order ignored).
    Otherwise, if similarity score >= 60 -> "needs_manual_verification"; below 60 -> "mismatch".
    None/empty/whitespace on either side returns "needs_manual_verification".
    """
    na = normalize_name(a)
    nb = normalize_name(b)

    if not na or not nb:
        return "needs_manual_verification", 0.0

    # Token sets for exact match check
    tokens_a = set(na.split())
    tokens_b = set(nb.split())

    if tokens_a == tokens_b and tokens_a:
        return "matched", 100.0

    if RAPIDFUZZ_AVAILABLE:
        score = float(fuzz.token_sort_ratio(na, nb))
    else:
        score = _jaccard_similarity(na, nb) * 100.0

    if score >= 60.0:
        return "needs_manual_verification", score
    else:
        return "mismatch", score


_SURVEY_PREFIX = re.compile(r"^(?:SYNO|SY\.?NO\.?|SURVEY\.?NO\.?|SITE\.?NO\.?|SURVEY|SY|SITE)\s*[:\-]?\s*", re.IGNORECASE)
_SURVEY_NO_PREFIX = re.compile(r"^NO\.?\s*", re.IGNORECASE)
_SURVEY_CLEAN = re.compile(r"[^\w/.-]")
_SURVEY_SEP = re.compile(r"[\s\-/]+")


def normalize_survey_number(survey: str) -> str:
    """
    Normalize survey number to canonical form:
    - Remove prefixes (Sy.No, Survey No, etc.)
    - Remove spaces, uppercase
    - Standardize separators to /
    - e.g., "Sy.No 45/2", "45-2", "Survey No. 45/2" -> "45/2"
    """
    if not survey:
        return ""

    s = survey.strip()
    # Apply prefix removal repeatedly until no more matches
    for _ in range(3):
        new_s = _SURVEY_PREFIX.sub("", s)
        if new_s == s:
            break
        s = new_s
    # Remove any remaining "NO." prefix
    s = _SURVEY_NO_PREFIX.sub("", s)
    s = s.upper()
    s = _SURVEY_CLEAN.sub("", s)
    s = _SURVEY_SEP.sub("/", s)
    s = s.strip("/")
    return s


_DATE_PATTERNS = [
    (re.compile(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$"), lambda m: date(int(m.group(3)), int(m.group(2)), int(m.group(1)))),
    (re.compile(r"^(\d{4})[/-](\d{1,2})[/-](\d{1,2})$"), lambda m: date(int(m.group(1)), int(m.group(2)), int(m.group(3)))),
    (re.compile(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{2})$"), lambda m: date(2000 + int(m.group(3)), int(m.group(2)), int(m.group(1)))),
]


_MONTH_NAMES = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "september": 9, "oct": 10, "october": 10,
    "nov": 11, "november": 11, "dec": 12, "december": 12,
}


def parse_date(value: str) -> Optional[date]:
    """
    Parse common date formats:
    - dd/mm/yyyy, dd-mm-yyyy
    - yyyy-mm-dd
    - "12 March 2019", "12 Mar 2019"
    Returns date or None if unparseable.
    """
    if not value:
        return None

    s = value.strip()
    for pattern, parser in _DATE_PATTERNS:
        m = pattern.match(s)
        if m:
            try:
                return parser(m)
            except ValueError:
                continue

    parts = re.split(r"[\s\-/]+", s)
    if len(parts) == 3:
        try:
            d = int(parts[0])
            m_str = parts[1].lower()[:3]
            y = int(parts[2])
            if m_str in _MONTH_NAMES:
                return date(y, _MONTH_NAMES[m_str], d)
            m = int(parts[1])
            return date(y, m, d)
        except (ValueError, KeyError):
            pass

    return None


_UNIT_FACTORS = {
    "sqft": 1.0,
    "sq_ft": 1.0,
    "sqft": 1.0,
    "square_feet": 1.0,
    "sqm": 10.7639,
    "sq_m": 10.7639,
    "sq_meter": 10.7639,
    "square_meter": 10.7639,
    "square_meters": 10.7639,
    "gunta": 1089.0,
    "guntas": 1089.0,
    "guntha": 1089.0,
    "gunthas": 1089.0,
    "acre": 43560.0,
    "acres": 43560.0,
}


def to_sqft(value: float, unit: str) -> float:
    """
    Convert area value to square feet.
    Supported units: sqft, sqm, guntas, acres
    """
    if not unit:
        return value

    key = unit.strip().lower().replace(" ", "_").replace(".", "").replace("-", "_")
    factor = _UNIT_FACTORS.get(key)
    if factor is None:
        return value
    return value * factor


def areas_match(a_sqft: float, b_sqft: float, tolerance: float = 0.05) -> Tuple[bool, float]:
    """
    Compare two areas in sqft.
    Returns (is_match, diff_percentage)
    """
    if a_sqft <= 0 or b_sqft <= 0:
        return False, 100.0

    diff = abs(a_sqft - b_sqft)
    pct = diff / max(a_sqft, b_sqft)
    return pct <= tolerance, pct * 100.0
