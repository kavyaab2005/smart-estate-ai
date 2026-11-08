from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from uuid import UUID

from app.database import get_db
from app.models.user import User
from app.models.property import Property
from app.models.common import FraudAnalysis, PropertyImage, Document, DocumentVerification, VerificationStatusEnum
from app.schemas.property import PropertyCreate, PropertyUpdate, PropertyResponse
from app.core.deps import get_current_user, require_role

from fastapi import UploadFile, File
import shutil
import uuid as uuid_lib
import os

router = APIRouter(prefix="/properties", tags=["properties"])


@router.post("", response_model=PropertyResponse)
def create_property(
    payload: PropertyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("agent", "admin")),
):
    new_property = Property(agent_id=current_user.id, **payload.model_dump())
    db.add(new_property)
    db.commit()
    db.refresh(new_property)
    return new_property


@router.get("")
def list_properties(
    city: Optional[str] = Query(None),
    listing_type: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    bhk: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Property).filter(Property.status == "approved")

    if city:
        query = query.filter(Property.city.ilike(f"%{city}%"))
    if listing_type:
        query = query.filter(Property.listing_type == listing_type)
    if min_price is not None:
        query = query.filter(Property.price >= min_price)
    if max_price is not None:
        query = query.filter(Property.price <= max_price)
    if bhk is not None:
        query = query.filter(Property.bhk == bhk)

    total = query.count()
    properties = query.all()

    property_ids = [p.id for p in properties]

    trust_scores = {}
    if property_ids:
        latest_trust = db.query(
            FraudAnalysis.property_id,
            FraudAnalysis.trust_score
        ).filter(
            FraudAnalysis.property_id.in_(property_ids)
        ).distinct(FraudAnalysis.property_id).order_by(
            FraudAnalysis.property_id,
            FraudAnalysis.created_at.desc()
        ).all()

        trust_scores = {row.property_id: row.trust_score for row in latest_trust}

    images = db.query(PropertyImage).filter(PropertyImage.property_id.in_(property_ids)).all()
    images_by_property = {}
    for img in images:
        images_by_property.setdefault(img.property_id, []).append(img.image_url)

    results = []
    for p in properties:
        item = PropertyResponse.model_validate(p).model_dump()
        item["images"] = images_by_property.get(p.id, [])
        item["trust_score"] = trust_scores.get(p.id)
        results.append(item)

    return {
        "properties": results,
        "total": total,
    }

@router.get("/mine")
def list_my_properties(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    properties = db.query(Property).filter(Property.agent_id == current_user.id).all()

    property_ids = [p.id for p in properties]
    images = db.query(PropertyImage).filter(PropertyImage.property_id.in_(property_ids)).all()
    images_by_property = {}
    for img in images:
        images_by_property.setdefault(img.property_id, []).append(img.image_url)

    results = []
    for p in properties:
        item = PropertyResponse.model_validate(p).model_dump()
        item["images"] = images_by_property.get(p.id, [])
        results.append(item)

    return {"properties": results}
def _get_trust_signals(db: Session, property_id: UUID) -> dict:
    """Get aggregated trust signals from document verifications for a property."""
    # Get all documents for this property
    docs = db.query(Document).filter(Document.property_id == property_id).all()
    doc_ids = [d.id for d in docs]
    
    if not doc_ids:
        return {}
    
    # Get latest verification for each document
    verifications = db.query(DocumentVerification).filter(
        DocumentVerification.document_id.in_(doc_ids)
    ).order_by(DocumentVerification.document_id, DocumentVerification.created_at.desc()).all()
    
    # Aggregate match results from all verifications
    signals = {}
    for v in verifications:
        match_results = v.match_result_json
        # Handle both formats: list (old) or dict with "matches" key (new)
        if isinstance(match_results, list):
            matches = match_results
        elif isinstance(match_results, dict):
            matches = match_results.get("matches", [])
        else:
            matches = []
            
        for match in matches:
            field = match.get("field")
            status = match.get("status")
            if field and status:
                # Map document verification fields to trust signals
                # OCR verification produces: owner_name, property_address, survey_number, 
                # registration_number, area, document_date
                field_mapping = {
                    "registration_number": "rera_status",
                    "survey_number": "encumbrance_status",
                    "property_address": "title_clarity",
                    "owner_name": "owner_match",
                    "area": "title_clarity",
                    "document_date": "title_clarity",
                }
                signal_key = field_mapping.get(field)
                if signal_key and signal_key not in signals:
                    status_mapping = {
                        "match": "verified",
                        "mismatch": "unregistered",
                        "pending": "pending",
                        "not_found": "pending",
                        "not_applicable": "not_applicable",
                    }
                    signals[signal_key] = status_mapping.get(status, status)
    
    # document_completeness: ratio of signals we have
    expected_signals = ["rera_status", "encumbrance_status", "title_clarity", "owner_match"]
    signals["document_completeness"] = len([s for s in expected_signals if s in signals]) / len(expected_signals)
    
    return signals


@router.get("/{property_id}")
def get_property(property_id: UUID, db: Session = Depends(get_db)):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    images = (
        db.query(PropertyImage)
        .filter(PropertyImage.property_id == property_id)
        .all()
    )
    image_urls = [img.image_url for img in images]

    amenity_names = [a.name for a in prop.amenities] if hasattr(prop, "amenities") else []
    
    trust_signals = _get_trust_signals(db, property_id)

    return {
        "property": PropertyResponse.model_validate(prop),
        "images": image_urls,
        "amenities": amenity_names,
        "trust_signals": trust_signals,
    }


@router.get("/{property_id}/trust-signals")
def get_trust_signals(property_id: UUID, db: Session = Depends(get_db)):
    """Get trust verification signals for a property."""
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    trust_signals = _get_trust_signals(db, property_id)
    return {"property_id": str(property_id), "trust_signals": trust_signals}


@router.put("/{property_id}", response_model=PropertyResponse)
def update_property(
    property_id: UUID,
    payload: PropertyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    if prop.agent_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to edit this property")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(prop, key, value)

    db.commit()
    db.refresh(prop)
    return prop


@router.delete("/{property_id}")
def delete_property(
    property_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    if prop.agent_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete this property")

    db.delete(prop)
    db.commit()
    return {"message": "Property deleted successfully"}


@router.post("/{property_id}/images")
def upload_property_image(
    property_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    if prop.agent_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to add images to this property")

    os.makedirs("uploads", exist_ok=True)
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"{uuid_lib.uuid4()}.{file_extension}"
    file_path = os.path.join("uploads", unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    image_url = f"/uploads/{unique_filename}"
    new_image = PropertyImage(property_id=property_id, image_url=image_url)
    db.add(new_image)
    db.commit()
    db.refresh(new_image)

    return {"image_url": image_url}

