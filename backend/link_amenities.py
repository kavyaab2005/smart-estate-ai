import sys
import random
sys.path.insert(0, '.')

from app.database import get_db
from app.models.common import Amenity, PropertyAmenity
from app.models.property import Property


def link_amenities():
    db = next(get_db())
    try:
        amenities = db.query(Amenity).all()
        if not amenities:
            print("No amenities found in database")
            return

        amenity_ids = [a.id for a in amenities]
        print(f"Found {len(amenity_ids)} amenities")

        properties = db.query(Property).all()
        print(f"Found {len(properties)} properties")

        linked_count = 0
        skipped_count = 0

        for prop in properties:
            # Check if property already has amenities
            existing = db.query(PropertyAmenity).filter(
                PropertyAmenity.property_id == prop.id
            ).count()

            if existing > 0:
                print(f"Skipping property {prop.id} ({prop.title}) - already has {existing} amenities")
                skipped_count += 1
                continue

            # Select random 4-9 amenities
            num_amenities = random.randint(4, min(9, len(amenity_ids)))
            selected_amenity_ids = random.sample(amenity_ids, num_amenities)

            for amenity_id in selected_amenity_ids:
                pa = PropertyAmenity(property_id=prop.id, amenity_id=amenity_id)
                db.add(pa)

            linked_count += 1
            print(f"Linked {num_amenities} amenities to property {prop.id} ({prop.title})")

        db.commit()
        print(f"\nDone! Linked amenities to {linked_count} properties, skipped {skipped_count} properties.")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    link_amenities()