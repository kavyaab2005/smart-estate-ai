from app.database import SessionLocal
from app.models.property import Property
from app.rag.vector_store import upsert_property, collection_count, reset_collection


def property_to_text(p: Property) -> str:
    parts = [
        f"{p.bhk} BHK {p.property_type or ''} for {p.listing_type.value if p.listing_type else ''}",
        f"in {p.city or 'unknown city'}",
        f"priced at {p.price} rupees" if p.price else "",
        f"area {p.area_sqft} sqft" if p.area_sqft else "",
        f"{p.bathrooms} bathrooms" if p.bathrooms else "",
        f"located at {p.address}" if p.address else "",
        f"furnishing: {p.furnishing}" if p.furnishing else "",
        "has parking" if p.parking else "no parking",
        p.description or "",
    ]
    return ". ".join([part for part in parts if part])


def run():
    db = SessionLocal()
    reset_collection()
    try:
        properties = db.query(Property).filter(Property.status == "approved").all()
        print(f"Found {len(properties)} approved properties in DB")

        for p in properties:
            text = property_to_text(p)
            metadata = {
                "title": p.title,
                "city": p.city or "",
                "price": float(p.price) if p.price else 0,
                "bhk": p.bhk or 0,
                "property_type": p.property_type or "",
                "listing_type": p.listing_type.value if p.listing_type else "",
            }
            upsert_property(str(p.id), text, metadata)

        print(f"Indexed. Total vectors in store: {collection_count()}")
    finally:
        db.close()


if __name__ == "__main__":
    run()