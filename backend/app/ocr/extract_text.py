import io
import logging
from typing import Any, Dict, List, Union

from PIL import Image

from app.ocr.preprocess import preprocess_image

logger = logging.getLogger(__name__)

# A PDF page with at least this many characters is treated as having a real text layer
MIN_TEXT_CHARS = 40
# Safety limit so a huge upload cannot hang the server
MAX_PAGES = 10

PYTESSERACT_AVAILABLE = False
PDF2IMAGE_AVAILABLE = False
PYPDF_AVAILABLE = False
OCR_READY = False  # True only if the Tesseract program itself is installed

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
    try:
        pytesseract.get_tesseract_version()
        OCR_READY = True
    except Exception:
        logger.warning("Tesseract program not found. Scanned documents cannot be read.")
except ImportError:
    logger.warning("pytesseract library not found.")

try:
    from pdf2image import convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    logger.warning("pdf2image library not found.")

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    logger.warning("pypdf library not found.")


def _looks_garbled(text: str) -> bool:
    """True if the PDF text layer is mostly symbols (broken Kannada font encoding)."""
    letters = [c for c in text if not c.isspace()]
    if not letters:
        return False
    odd = sum(1 for c in letters if ord(c) > 127 and not (0x0C80 <= ord(c) <= 0x0CFF))
    return odd / len(letters) > 0.2


def extract_text_from_image(image_input: Union[Image.Image, bytes, str], preprocess: bool = True) -> str:
    """OCR a single image (PIL Image, bytes, or file path). Returns '' if OCR is unavailable."""
    if isinstance(image_input, (bytes, str)):
        img = Image.open(io.BytesIO(image_input) if isinstance(image_input, bytes) else image_input)
    else:
        img = image_input

    if not OCR_READY:
        return ""

    processed = preprocess_image(img) if preprocess else img
    try:
        try:
            return (pytesseract.image_to_string(processed, lang="eng+kan") or "").strip()
        except Exception:
            return (pytesseract.image_to_string(processed) or "").strip()
    except Exception as e:
        logger.warning(f"OCR failed: {e}")
        return ""


def extract_pdf_with_meta(pdf_bytes: bytes, preprocess: bool = True) -> Dict[str, Any]:
    """
    Reads a PDF page by page.
    Text-based pages use the built-in text layer (fast and exact).
    Pages without a text layer (scans) are sent to OCR.
    """
    pages_text: List[str] = []
    methods: List[str] = []
    warnings: List[str] = []

    reader = None
    if PYPDF_AVAILABLE:
        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        except Exception as e:
            warnings.append(f"pdf_unreadable: {e}")

    total_pages = len(reader.pages) if reader else 1
    if total_pages > MAX_PAGES:
        warnings.append(f"page_limit: only first {MAX_PAGES} of {total_pages} pages read")
    page_count = min(total_pages, MAX_PAGES)

    for i in range(page_count):
        text = ""
        if reader:
            try:
                text = (reader.pages[i].extract_text() or "").strip()
            except Exception:
                text = ""

        if len(text) >= MIN_TEXT_CHARS and not _looks_garbled(text):
            pages_text.append(text)
            methods.append("text_layer")
            continue

        # No usable text layer on this page: fall back to OCR
        if not (OCR_READY and PDF2IMAGE_AVAILABLE):
            warnings.append(f"page_{i + 1}_needs_ocr_but_ocr_unavailable")
            continue
        try:
            imgs = convert_from_bytes(pdf_bytes, first_page=i + 1, last_page=i + 1, dpi=200)
            ocr_text = extract_text_from_image(imgs[0], preprocess=preprocess) if imgs else ""
        except Exception as e:
            warnings.append(f"page_{i + 1}_ocr_failed: {e}")
            ocr_text = ""
        if ocr_text:
            pages_text.append(ocr_text)
            methods.append("ocr")

    return {
        "text": "\n\n".join(pages_text).strip(),
        "pages_read": len(pages_text),
        "methods": methods,
        "warnings": warnings,
    }


def extract_text_with_meta(file_bytes: bytes, filename: str, preprocess: bool = True) -> Dict[str, Any]:
    """Like extract_text_from_file, but also reports HOW the text was obtained."""
    name = filename.lower()
    if name.endswith(".pdf"):
        return extract_pdf_with_meta(file_bytes, preprocess=preprocess)
    if name.endswith(".txt"):
        return {"text": file_bytes.decode("utf-8", errors="ignore"), "pages_read": 1,
                "methods": ["plain_text"], "warnings": []}

    # Images (and unknown types, tried as images)
    warnings: List[str] = []
    try:
        text = extract_text_from_image(file_bytes, preprocess=preprocess)
    except Exception as e:
        text = ""
        warnings.append(f"image_unreadable: {e}")
    if not text and not OCR_READY:
        warnings.append("ocr_unavailable")
    return {"text": text, "pages_read": 1 if text else 0,
            "methods": ["ocr"] if text else [], "warnings": warnings}


def extract_text_from_file(file_bytes: bytes, filename: str, preprocess: bool = True) -> str:
    """Backward-compatible wrapper: returns only the text, as the router expects."""
    return extract_text_with_meta(file_bytes, filename, preprocess)["text"]