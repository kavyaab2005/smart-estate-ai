import io
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False
    pypdf = None  # type: ignore

try:
    from pdf2image import convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    convert_from_bytes = None  # type: ignore


@dataclass
class PageText:
    page: int
    text: str
    method: str
    warnings: List[str]


def read_pages(file_bytes: bytes, filename: str) -> List[PageText]:
    """
    Read text from a file page by page.
    Returns list of PageText with page number (1-based), text, method, and warnings.
    Never raises on bad input; returns error entries instead.
    """
    name = filename.lower()
    if name.endswith(".pdf"):
        return _read_pdf_pages(file_bytes)
    elif name.endswith((".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp")):
        return _read_image_page(file_bytes)
    elif name.endswith(".txt"):
        return _read_text_file(file_bytes)
    else:
        # Unknown type - try as image
        return _read_image_page(file_bytes)


def _read_pdf_pages(pdf_bytes: bytes) -> List[PageText]:
    pages: List[PageText] = []
    warnings: List[str] = []

    if not PYPDF_AVAILABLE:
        warnings.append("pypdf not available; cannot read PDF text layer")
        return [PageText(page=1, text="", method="error", warnings=warnings)]

    reader = None
    try:
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    except Exception as e:
        warnings.append(f"pdf_unreadable: {e}")
        return [PageText(page=1, text="", method="error", warnings=warnings)]

    total_pages = len(reader.pages)
    MIN_TEXT_CHARS = 40

    for i in range(total_pages):
        page_num = i + 1
        page_warnings: List[str] = []
        text = ""
        method = "none"

        if reader:
            try:
                text = (reader.pages[i].extract_text() or "").strip()
            except Exception as e:
                page_warnings.append(f"text_layer_failed: {e}")
                text = ""

        if len(text) >= MIN_TEXT_CHARS:
            method = "text_layer"
        else:
            method = "needs_ocr"
            if not PDF2IMAGE_AVAILABLE:
                page_warnings.append("ocr_unavailable: pdf2image not installed")

        pages.append(PageText(page=page_num, text=text, method=method, warnings=page_warnings))

    return pages


def _read_image_page(file_bytes: bytes) -> List[PageText]:
    return [PageText(page=1, text="", method="needs_ocr", warnings=["ocr_not_implemented_phase2a"])]


def _read_text_file(file_bytes: bytes) -> List[PageText]:
    try:
        text = file_bytes.decode("utf-8", errors="ignore")
        return [PageText(page=1, text=text, method="plain_text", warnings=[])]
    except Exception as e:
        return [PageText(page=1, text="", method="error", warnings=[f"text_decode_failed: {e}"])]
