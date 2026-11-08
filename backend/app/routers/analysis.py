from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.database import get_db
from app.models.property import Property
from app.analysis.property_score import analyze_property
from app.schemas.ai_schemas import AnalyzePropertyResponse
from app.core.deps import get_current_user_optional
from app.models.user import User

router = APIRouter(prefix="/properties", tags=["Property Analysis"])


@router.get("/{property_id}/analyze", response_model=AnalyzePropertyResponse)
def analyze_property_endpoint(
    property_id: UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    user_id = str(current_user.id) if current_user else None
    result = analyze_property(str(property_id), user_id=user_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return AnalyzePropertyResponse(**result)