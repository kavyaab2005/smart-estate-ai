import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.database import Base, engine
import app.models.user
import app.models.property
import app.models.common
import app.models.inquiry

Base.metadata.create_all(bind=engine)

from app.routers import (
    auth, properties, favorites, saved_searches, admin, ml_router,
    inquiries, ai_assistant, financials, analytics, forecasting, 
    security_audit, sustainability, documents, chatbot, recommendations, location, analysis
)
app = FastAPI(
    title="SmartEstate AI Backend - Enterprise Edition",
    description="AI-powered Real Estate Platform with Valuation, Forecasting, Security, Sustainability & Document Intelligence APIs",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("JWT_SECRET", "secret_key"))

os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Register All Routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(properties.router, prefix="/api/v1")
app.include_router(favorites.router, prefix="/api/v1")
app.include_router(saved_searches.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(ml_router.router, prefix="/api/v1")
app.include_router(inquiries.router, prefix="/api/v1")
app.include_router(ai_assistant.router, prefix="/api/v1")
app.include_router(financials.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(forecasting.router, prefix="/api/v1")
app.include_router(security_audit.router, prefix="/api/v1")
app.include_router(sustainability.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(chatbot.router, prefix="/api/v1")
app.include_router(recommendations.router, prefix="/api/v1")
app.include_router(location.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")

@app.get("/")
def root():
    return {
        "message": "SmartEstate AI Enterprise backend is active",
        "docs_url": "http://localhost:8000/docs"
    }