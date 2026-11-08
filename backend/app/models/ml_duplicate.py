from pydantic import BaseModel
from typing import List, Optional

class DuplicateCheckRequest(BaseModel):
    property_id: Optional[str] = None
    title: str
    description: str
    city: str
    price: float
    area_sqft: float

class SimilarProperty(BaseModel):
    similar_property_text: str
    similarity_score: float

class DuplicateCheckResponse(BaseModel):
    is_duplicate: bool
    duplicates: List[SimilarProperty]