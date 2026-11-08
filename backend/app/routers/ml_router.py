from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from uuid import UUID
from datetime import datetime

from app.database import get_db, engine
from app.models.common import FraudAnalysis
from app.models.ml_price import PropertyPriceRequest, PropertyPriceResponse
from app.models.ml_fraud import FraudScoreRequest, FraudScoreResponse
from app.models.ml_duplicate import DuplicateCheckRequest, DuplicateCheckResponse

from ml.price_predictor import predictor
from ml.fraud_scorer import fraud_scorer
from ml.duplicate_detector import duplicate_detector

router = APIRouter(tags=["ML Services"])


@router.post("/predict/price", response_model=PropertyPriceResponse)
def predict_price(data: PropertyPriceRequest):
    try:
        return predictor.predict(
            property_type=data.property_type,
            listing_type=data.listing_type,
            area_sqft=data.area_sqft,
            bhk=data.bhk,
            bedrooms=data.bedrooms,
            floor=data.floor,
            total_floors=data.total_floors,
            property_age_years=data.property_age_years,
            furnishing=data.furnishing,
            parking=data.parking,
            city=data.city,
            amenities=data.amenities,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fraud/score", response_model=FraudScoreResponse)
def fraud_score(data: FraudScoreRequest, db: Session = Depends(get_db)):
    try:
        result = fraud_scorer.score(
            property_type=data.property_type,
            listing_type=data.listing_type,
            price=data.price,
            area_sqft=data.area_sqft,
            bhk=data.bhk,
            bedrooms=data.bedrooms,
            floor=data.floor,
            total_floors=data.total_floors,
            property_age_years=data.property_age_years,
            furnishing=data.furnishing,
            parking=data.parking,
            city=data.city,
            amenities=data.amenities,
            is_verified=data.is_verified,
        )

        if data.property_id:
            property_id = UUID(data.property_id)
            existing = db.query(FraudAnalysis).filter(FraudAnalysis.property_id == property_id).first()
            reasons_json = [{"level": f["level"], "reason": f["reason"]} for f in result["flags"]] + \
                           [{"level": "info", "reason": r} for r in result["reasons"]]

            now = datetime.utcnow()
            if existing:
                db.delete(existing)
            new_analysis = FraudAnalysis(
                property_id=property_id,
                trust_score=result["trust_score"],
                risk_level=result["risk_level"],
                reasons_json=reasons_json,
                created_at=now,
            )
            db.add(new_analysis)
            db.commit()

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/web-duplicate", response_model=DuplicateCheckResponse)
def check_duplicate(data: DuplicateCheckRequest):
    try:
        return duplicate_detector.check(
            title=data.title,
            description=data.description,
            city=data.city,
            price=data.price,
            area_sqft=data.area_sqft,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))