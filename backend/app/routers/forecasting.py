from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from uuid import UUID
from sqlalchemy.orm import Session
from app.services.forecasting import forecast_property_value
from app.database import get_db
from app.models.property import Property

router = APIRouter(prefix="/forecasting", tags=["AI Price Forecasting"])

class ForecastRequest(BaseModel):
    current_price: float
    city: str
    years: int = 5
    property_id: UUID | None = None

@router.post("/predict")
def predict_appreciation(req: ForecastRequest, db: Session = Depends(get_db)):
    # If property_id is provided, validate it exists
    if req.property_id:
        prop = db.query(Property).filter(Property.id == req.property_id).first()
        if not prop:
            raise HTTPException(status_code=404, detail="Property not found")
        # Use property's city if not provided in request
        city = req.city or (prop.city if prop else "default")
    else:
        city = req.city

    return forecast_property_value(req.current_price, city, req.years, str(req.property_id) if req.property_id else None)
