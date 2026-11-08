from fastapi import APIRouter
from pydantic import BaseModel
from app.services.fraud_detector import analyze_listing_fraud_risk

router = APIRouter(prefix="/security", tags=["Listing Security & Fraud Audit"])

class FraudAuditRequest(BaseModel):
    title: str
    description: str = ""
    price: float
    area_sqft: float
    city: str

@router.post("/audit-listing")
def audit_listing(req: FraudAuditRequest):
    return analyze_listing_fraud_risk(
        req.title, req.description, req.price, req.area_sqft, req.city
    )
