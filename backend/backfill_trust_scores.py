import os
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.property import Property
from app.models.user import User
from app.models.common import FraudAnalysis
from uuid import UUID
from datetime import datetime
from ml.fraud_scorer import fraud_scorer


def main():
    db = SessionLocal()
    try:
        properties = db.query(Property).all()
        total = len(properties)
        print(f"Found {total} properties to process")

        scored = 0
        failed = 0
        failures = []

        for idx, prop in enumerate(properties, 1):
            try:
                agent = None
                if prop.agent_id:
                    agent = db.query(User).filter(User.id == prop.agent_id).first()

                is_verified = bool(agent and agent.is_verified) if agent else False

                result = fraud_scorer.score(
                    property_type=prop.property_type.value if prop.property_type else "apartment",
                    listing_type=prop.listing_type.value if prop.listing_type else "buy",
                    price=float(prop.price) if prop.price else 0.0,
                    area_sqft=float(prop.area_sqft) if prop.area_sqft else 0.0,
                    bhk=prop.bhk or 0,
                    bedrooms=prop.bathrooms or prop.bhk or 0,
                    floor=prop.floor or 0,
                    total_floors=prop.total_floors or 0,
                    property_age_years=prop.property_age_years or 0,
                    furnishing=prop.furnishing or "unfurnished",
                    parking=1 if prop.parking else 0,
                    city=prop.city or "Unknown",
                    amenities=[],
                    is_verified=is_verified,
                )

                reasons_json = [{"level": f["level"], "reason": f["reason"]} for f in result["flags"]] + \
                               [{"level": "info", "reason": r} for r in result["reasons"]]

                existing = db.query(FraudAnalysis).filter(FraudAnalysis.property_id == prop.id).first()
                now = datetime.utcnow()

                if existing:
                    db.delete(existing)

                new_analysis = FraudAnalysis(
                    property_id=prop.id,
                    trust_score=result["trust_score"],
                    risk_level=result["risk_level"],
                    reasons_json=reasons_json,
                    created_at=now,
                )
                db.add(new_analysis)
                scored += 1

                if idx % 20 == 0:
                    db.commit()
                    print(f"  Processed {idx}/{total}...")

            except Exception as e:
                failed += 1
                failures.append((str(prop.id), str(e)))
                print(f"  Failed property {prop.id}: {e}")
                continue

        db.commit()
        print(f"\n=== Backfill Complete ===")
        print(f"Total properties: {total}")
        print(f"Successfully scored: {scored}")
        print(f"Failed: {failed}")

        if failures:
            print("\nFailures:")
            for prop_id, error in failures:
                print(f"  {prop_id}: {error}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
