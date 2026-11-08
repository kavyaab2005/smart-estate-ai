from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.property import Property
from app.services.ai_advisor import query_ai_real_estate_advisor

router = APIRouter(prefix="/ai-assistant", tags=["AI Assistant"])

class ChatMessageRequest(BaseModel):
    message: str

@router.post("/chat")
def chat_with_assistant(req: ChatMessageRequest, db: Session = Depends(get_db)):
    properties = db.query(Property).limit(30).all()
    prop_dicts = [
        {
            "id": str(p.id),
            "title": p.title,
            "price": float(p.price) if p.price else 0,
            "bhk": p.bhk,
            "city": p.city
        }
        for p in properties
    ]
    reply = query_ai_real_estate_advisor(req.message, prop_dicts)
    return {"reply": reply}
