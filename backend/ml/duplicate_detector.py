import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List

from app.database import SessionLocal
from app.models.property import Property

THRESHOLD = 0.75


class DuplicateDetector:
    """
    Compares a new/edited listing against the REAL properties currently in the
    database (not a static training file), so it can catch genuine duplicate
    or near-duplicate listings as they're created.
    """

    def check(self, title: str, description: str, city: str,
              price: float, area_sqft: float, exclude_property_id: str = None) -> dict:

        db = SessionLocal()
        try:
            properties = db.query(Property).all()
        finally:
            db.close()

        if exclude_property_id:
            properties = [p for p in properties if str(p.id) != str(exclude_property_id)]

        if not properties:
            return {"is_duplicate": False, "duplicates": []}

        texts = [
            f"{p.title or ''} {p.description or ''} {p.city or ''}"
            for p in properties
        ]

        vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        tfidf = vec.fit_transform(texts)

        query = f"{title} {description} {city}"
        qvec = vec.transform([query])
        sims = cosine_similarity(qvec, tfidf).flatten()

        results = []
        for idx in np.where(sims >= THRESHOLD)[0]:
            prop = properties[idx]
            score = float(sims[idx])

            prop_price = float(prop.price or 0)
            prop_area = float(prop.area_sqft or 0)
            if (abs(prop_price - price) / max(price, 1) < 0.1 and
                    abs(prop_area - area_sqft) / max(area_sqft, 1) < 0.1):
                score = min(1.0, score * 1.1)

            if score >= THRESHOLD:
                results.append({
                    "similar_property_text": prop.title or "Unknown",
                    "similarity_score": round(score, 3),
                })

        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return {"is_duplicate": len(results) > 0, "duplicates": results[:5]}


duplicate_detector = DuplicateDetector()