from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.recommendation.content_based import get_recommendations
from app.schemas.ai_schemas import RecommendationsResponse, RecommendationItem
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get("", response_model=RecommendationsResponse)
def get_user_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    results = get_recommendations(str(current_user.id))

    return RecommendationsResponse(
        recommendations=[RecommendationItem(**r) for r in results]
    )