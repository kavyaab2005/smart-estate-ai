# SmartEstate AI

**An AI-powered real estate platform for buyers, agents and admins: search listings, verify property documents, and get data-driven insight on every property.**

Final-year B.E. (CSE - AI/ML) project, built entirely on free-tier services.

<!-- Add screenshots here once they are saved in docs/screenshots/, for example:
![Landing page](docs/screenshots/landing.png)
-->

---

## Features

**For buyers**
- Property search with filters, plus an interactive map view (Leaflet)
- Side-by-side property comparison and a favorites list
- A property detail page with tabs for AI analysis, price forecast, location intelligence, sustainability estimate and an EMI calculator
- Contact the listing agent with an inquiry
- AI chat assistant that answers questions about listings (RAG)

**For agents**
- Create and edit listings, with photo uploads
- Upload property documents for automated verification and a trust score

**For admins**
- Admin dashboard and listing review, with flagged listings surfaced for manual checks

**AI and ML**
- Price prediction model trained on a Bengaluru property dataset
- Fraud scoring and duplicate-listing detection
- RAG chatbot: sentence-transformers embeddings, ChromaDB vector store, Groq LLM
- Content-based property recommendations
- Composite property analysis score
- Price forecasting and sustainability (solar / CO2) estimates
- Location intelligence from OpenStreetMap (Overpass API), with a labelled fallback when the API is unavailable
- Document Intelligence: OCR extraction and fuzzy verification of property documents
- Trust suite: cross-checks extracted document details, computes a trust score and applies review rules

---

## Tech Stack

| Layer | Technologies |
|---|---|
| Frontend | React, Vite, Tailwind CSS v4, React Router, Axios, Leaflet / react-leaflet, Recharts, lucide-react |
| Backend | Python, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 |
| Database | PostgreSQL |
| Auth | JWT (python-jose), bcrypt / passlib, Authlib (Google OAuth) |
| AI / ML | scikit-learn, XGBoost, sentence-transformers, ChromaDB, Groq API, rapidfuzz |
| Document processing | pytesseract, pdf2image, Pillow, pypdf |
| Geo | geopy, OpenStreetMap Overpass API |

---

## Project Structure

```
smart-estate-ai/
|-- backend/
|   |-- app/
|   |   |-- routers/        # REST endpoints (properties, auth, chat, documents, ...)
|   |   |-- services/       # Forecasting, fraud detection, sustainability, geo, AI advisor
|   |   |-- rag/            # Chatbot, embeddings, vector store
|   |   |-- ocr/            # OCR extraction and document verification
|   |   |-- trust_suite/    # Document trust scoring and review rules
|   |   |-- models/         # SQLAlchemy models
|   |   `-- schemas/        # Pydantic schemas
|   |-- alembic/            # Database migrations
|   |-- ml/                 # Price model, fraud scorer, duplicate detector
|   `-- requirements.txt
|-- frontend/
|   `-- src/                # React app (pages, components, api client)
`-- tests/                  # OCR pipeline tests and sample documents
```

---

## Getting Started

### Prerequisites

- Python 3.11 or newer
- Node.js (LTS)
- A PostgreSQL database (a free Neon database works well)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) and [Poppler](https://poppler.freedesktop.org/) installed and on your PATH (needed for document OCR)
- A free [Groq](https://console.groq.com/) API key for the AI chat assistant

### 1. Clone the repository

```bash
git clone https://github.com/kavyaab2005/smart-estate-ai.git
cd smart-estate-ai
```

### 2. Backend

```bash
cd backend
python -m venv venv

# Windows (PowerShell)
venv\Scripts\activate
# macOS / Linux
# source venv/bin/activate

pip install -r requirements.txt
```

Create your environment file and fill in the values:

```bash
# Windows
copy .env.example .env
# macOS / Linux
# cp .env.example .env
```

Never commit your real `.env` file. It is already listed in `.gitignore`.

Create the database tables and start the server:

```bash
alembic upgrade head
python seed.py          # optional: loads sample properties
uvicorn app.main:app --reload
```

To build the chatbot's vector index from the properties in your database:

```bash
python -m app.rag.embed_properties
```

- Backend: `http://127.0.0.1:8000`
- Interactive API docs (Swagger): `http://127.0.0.1:8000/docs`

### 3. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the address Vite prints (usually `http://localhost:5173`).

---

## Author

Built by **Kavya B** ([@kavyaab2005](https://github.com/kavyaab2005)).