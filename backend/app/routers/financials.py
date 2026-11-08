from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/financials", tags=["Financial Analytics"])

class MortgageRequest(BaseModel):
    property_price: float
    down_payment_percent: float = 20.0
    interest_rate_annual: float = 6.5
    loan_tenure_years: int = 30
    estimated_monthly_rent: float = 0.0

@router.post("/calculate-mortgage")
def calculate_mortgage(req: MortgageRequest):
    down_payment = (req.down_payment_percent / 100.0) * req.property_price
    loan_amount = req.property_price - down_payment
    
    monthly_rate = (req.interest_rate_annual / 100.0) / 12
    total_months = req.loan_tenure_years * 12

    if monthly_rate > 0:
        emi = loan_amount * monthly_rate * ((1 + monthly_rate) ** total_months) / (((1 + monthly_rate) ** total_months) - 1)
    else:
        emi = loan_amount / total_months

    total_payment = emi * total_months
    total_interest = total_payment - loan_amount
    
    annual_rent = req.estimated_monthly_rent * 12
    gross_yield = (annual_rent / req.property_price * 100) if req.property_price > 0 else 0.0

    return {
        "property_price": req.property_price,
        "down_payment": round(down_payment, 2),
        "loan_amount": round(loan_amount, 2),
        "monthly_emi": round(emi, 2),
        "total_interest_payable": round(total_interest, 2),
        "total_amount_payable": round(total_payment, 2),
        "gross_rental_yield_percent": round(gross_yield, 2)
    }
