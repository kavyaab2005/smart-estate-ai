from fastapi import APIRouter
from pydantic import BaseModel
from app.services.sustainability import calculate_green_building_score

router = APIRouter(prefix="/sustainability", tags=["Green Building & Solar Potential"])

class EcoScoreRequest(BaseModel):
    area_sqft: float
    total_floors: int = 1
    parking: bool = True

@router.post("/evaluate")
def evaluate_eco_impact(req: EcoScoreRequest):
    return calculate_green_building_score(req.area_sqft, req.total_floors, req.parking)
