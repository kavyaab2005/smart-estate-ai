from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.models.property import Property
from app.location.location_intel import get_location_intel
from app.schemas.ai_schemas import LocationIntelResponse

router = APIRouter(prefix="/properties", tags=["Location Intelligence"])


@router.get("/{property_id}/location-intel", response_model=LocationIntelResponse)
def get_property_location_intel(
    property_id: UUID,
    db: Session = Depends(get_db),
):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    if not prop.latitude or not prop.longitude:
        raise HTTPException(status_code=400, detail="Property does not have coordinates set")

    result = get_location_intel(db, float(prop.latitude), float(prop.longitude), str(property_id), city=prop.city)
    return LocationIntelResponse(**result)