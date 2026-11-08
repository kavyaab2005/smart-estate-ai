import uuid
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Body

from app.schemas.document_schemas import (
    DocumentUploadResponse,
    DocumentVerifyResponse,
    DocumentResponse,
    PropertyVerifyTarget
)
from app.ocr.extract_text import extract_text_from_file
from app.ocr.field_extractor import extract_fields
from app.ocr.document_verifier import verify_document_fields, MANDATORY_DISCLAIMER

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/documents",
    tags=["Document Intelligence"]
)

# In-memory document storage for uploaded documents
DOCUMENTS_STORE: Dict[str, Dict[str, Any]] = {}

# Ensure local upload directory exists
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads", "documents")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    property_id: str = Form(...),
    doc_type: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Upload a property document (PDF or image).
    Returns document_id and accessible file_url.
    """
    doc_id = str(uuid.uuid4())
    file_bytes = await file.read()
    
    # Save file locally
    safe_filename = f"{doc_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    try:
        with open(file_path, "wb") as f:
            f.write(file_bytes)
    except Exception as e:
        logger.error(f"Failed to save document file: {e}")

    file_url = f"/static/documents/{safe_filename}"
    uploaded_at = datetime.utcnow()

    # Store document record
    DOCUMENTS_STORE[doc_id] = {
        "document_id": doc_id,
        "property_id": property_id,
        "doc_type": doc_type,
        "file_url": file_url,
        "file_path": file_path,
        "file_bytes": file_bytes,
        "filename": file.filename,
        "uploaded_at": uploaded_at,
        "verification": None
    }

    return DocumentUploadResponse(
        document_id=doc_id,
        file_url=file_url
    )


@router.post("/{document_id}/verify", response_model=DocumentVerifyResponse)
async def verify_document(
    document_id: str,
    target_property: Optional[PropertyVerifyTarget] = Body(None)
):
    """
    Runs OCR text extraction, field parsing, and fuzzy comparison against property record details.
    """
    if document_id not in DOCUMENTS_STORE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )

    doc_record = DOCUMENTS_STORE[document_id]
    file_bytes = doc_record["file_bytes"]
    filename = doc_record["filename"]

    # 1. OCR Extraction
    raw_text = extract_text_from_file(file_bytes, filename, preprocess=True)

    # 2. Field Extraction
    extracted_fields = extract_fields(raw_text)

    # 3. Target property record to verify against
    target_dict = target_property.model_dump() if target_property else {
        "property_id": doc_record.get("property_id")
    }

    # 4. Fuzzy comparison and verification report
    verification_result = verify_document_fields(extracted_fields, target_dict)

    # Update in-memory document record
    doc_record["verification"] = verification_result

    return DocumentVerifyResponse(
        extracted_fields=verification_result["extracted_fields"],
        match_results=verification_result["match_results"],
        overall_status=verification_result["overall_status"],
        disclaimer=verification_result["disclaimer"]
    )


@router.get("/property/{property_id}")
def get_documents_by_property(property_id: str):
    """
    Lists all documents (and their verification status) for a given property.
    """
    docs = [doc for doc in DOCUMENTS_STORE.values() if doc["property_id"] == property_id]
    return {"property_id": property_id, "documents": docs}


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str):
    """
    Fetches uploaded document details and verification status.
    """
    if document_id not in DOCUMENTS_STORE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )

    doc_record = DOCUMENTS_STORE[document_id]
    
    return DocumentResponse(
        document_id=doc_record["document_id"],
        property_id=doc_record["property_id"],
        doc_type=doc_record["doc_type"],
        file_url=doc_record["file_url"],
        uploaded_at=doc_record["uploaded_at"],
        verification=doc_record["verification"]
    )
