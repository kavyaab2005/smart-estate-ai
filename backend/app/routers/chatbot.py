from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from uuid import UUID
import json

from app.database import get_db
from app.models.common import ChatSession, ChatMessage, SenderEnum
from app.rag.chatbot import answer_query, sync_chromadb_with_db
from app.schemas.ai_schemas import ChatMessageRequest, ChatMessageResponse
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/chat", tags=["AI Chatbot"])


@router.post("/message", response_model=ChatMessageResponse)
def send_chat_message(
    payload: ChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Get or create the chat session
    if payload.session_id:
        session = db.query(ChatSession).filter(ChatSession.id == payload.session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
    else:
        session = ChatSession(user_id=current_user.id)
        db.add(session)
        db.commit()
        db.refresh(session)

    # Save the user's message
    user_msg = ChatMessage(
        session_id=session.id,
        sender=SenderEnum.user,
        message_text=payload.message,
    )
    db.add(user_msg)
    db.commit()

    # Run the RAG pipeline
    result = answer_query(payload.message, db=db)

    # Save the assistant's reply
    assistant_msg = ChatMessage(
        session_id=session.id,
        sender=SenderEnum.assistant,
        message_text=result["response_text"],
    )
    db.add(assistant_msg)
    db.commit()

    return ChatMessageResponse(
        session_id=session.id,
        response_text=result["response_text"],
        referenced_property_ids=result["referenced_property_ids"],
    )


@router.post("/message/stream")
def stream_chat_message(
    payload: ChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Get or create the chat session
    if payload.session_id:
        session = db.query(ChatSession).filter(ChatSession.id == payload.session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
    else:
        session = ChatSession(user_id=current_user.id)
        db.add(session)
        db.commit()
        db.refresh(session)

    # Save the user's message
    user_msg = ChatMessage(
        session_id=session.id,
        sender=SenderEnum.user,
        message_text=payload.message,
    )
    db.add(user_msg)
    db.commit()

    def generate():
        # Get the full answer first (we'll stream it word by word)
        result = answer_query(payload.message, db=db)
        full_text = result["response_text"]
        
        # Stream word by word
        words = full_text.split()
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"
        
        # Send completion with metadata
        yield f"data: {json.dumps({'chunk': '', 'done': True, 'referenced_property_ids': result['referenced_property_ids'], 'timing': result.get('timing', {}), 'filters_used': result.get('filters_used', {}), 'fallback': result.get('fallback', False)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/admin/resync-chromadb")
def resync_chromadb(db: Session = Depends(get_db)):
    count = sync_chromadb_with_db(db)
    return {"message": f"Successfully synced {count} properties to ChromaDB"}