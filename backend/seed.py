import random
from app.database import SessionLocal, engine, Base
from app.models.user import User, RoleEnum
from app.models.property import Property, ListingTypeEnum, PropertyStatusEnum, PropertyTypeEnum
from app.models.common import Amenity, PropertyImage
from app.core.security import hash_password

Base.metadata.create_all(bind=engine)

db = SessionLocal()

# --- Amenities ---
amenity_names = [
    "Swimming Pool", "Gym", "Parking", "24/7 Security", "Power Backup",
    "Lift", "Clubhouse", "Children's Play Area", "Garden", "CCTV",
    "Intercom", "Rainwater Harvesting", "Gas Pipeline", "Fire Safety", "Visitor Parking",
]

existing_amenities = {a.name for a in db.query(Amenity).all()}
for name in amenity_names:
    if name not in existing_amenities:
        db.add(Amenity(name=name))
db.commit()

# --- Sample agent user (only created if it doesn't exist) ---
agent_email = "seed.agent@example.com"
agent = db.query(User).filter(User.email == agent_email).first()
if not agent:
    agent = User(
        name="Seed Agent",
        email=agent_email,
        password_hash=hash_password("seedpass123"),
        role=RoleEnum.agent,
        is_verified=True,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)

# --- Bengaluru localities with realistic per-sqft price ranges (buy, in INR) ---
localities = [
    {"name": "Koramangala", "lat": 12.9352, "lng": 77.6245, "min_psf": 11000, "max_psf": 16000},
    {"name": "Indiranagar", "lat": 12.9784, "lng": 77.6408, "min_psf": 12000, "max_psf": 17000},
    {"name": "Whitefield", "lat": 12.9698, "lng": 77.7500, "min_psf": 6000, "max_psf": 9500},
    {"name": "HSR Layout", "lat": 12.9116, "lng": 77.6389, "min_psf": 8500, "max_psf": 12500},
    {"name": "Electronic City", "lat": 12.8452, "lng": 77.6602, "min_psf": 4500, "max_psf": 6500},
    {"name": "Marathahalli", "lat": 12.9569, "lng": 77.7011, "min_psf": 6000, "max_psf": 8500},
    {"name": "JP Nagar", "lat": 12.9077, "lng": 77.5906, "min_psf": 7500, "max_psf": 10500},
    {"name": "Jayanagar", "lat": 12.9308, "lng": 77.5838, "min_psf": 9000, "max_psf": 13000},
    {"name": "Yelahanka", "lat": 13.1007, "lng": 77.5963, "min_psf": 5000, "max_psf": 7000},
    {"name": "Sarjapur Road", "lat": 12.9010, "lng": 77.6874, "min_psf": 6500, "max_psf": 9500},
    {"name": "Bannerghatta Road", "lat": 12.8845, "lng": 77.5978, "min_psf": 5500, "max_psf": 8000},
    {"name": "Hebbal", "lat": 13.0358, "lng": 77.5970, "min_psf": 7000, "max_psf": 10000},
]

# These are the NAMES of PropertyTypeEnum members
property_types = ["apartment", "villa", "independent_house", "plot"]
furnishings = ["furnished", "semi-furnished", "unfurnished"]
titles = [
    "Spacious {bhk}BHK {ptype} in {city}",
    "Modern {bhk}BHK {ptype} near {city}",
    "Well-maintained {bhk}BHK {ptype} in {city}",
    "Cozy {bhk}BHK {ptype} in {city}",
    "Premium {bhk}BHK {ptype} close to tech parks, {city}",
]
plot_titles = [
    "Residential Plot in {city}",
    "DTCP Approved Plot in {city}",
    "Corner Plot in {city}",
    "Prime Land Parcel in {city}",
]

REAL_ESTATE_IMAGE_URLS = [
    "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1600607687644-aac4c3eac7f4?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1600585154526-990dced4db0d?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1560184897-ae75f418493e?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1560185127-6ed189bf02f4?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1502005229762-cf1b2da7c5d6?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1523217582562-09d0def993a6?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1494526585095-c41746248156?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1484154218962-a197022b5858?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1502672023488-70e25813eb80?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1568605114967-8130f3a36994?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1449844908441-8829872d2607?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1592595896551-12b371d546d5?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1600047509807-ba8f99d2cdde?w=800&h=600&fit=crop",
]

existing_count = db.query(Property).count()

if existing_count < 5:
    for i in range(30):
        locality = random.choice(localities)
        ptype = random.choice(property_types)
        ptype_label = ptype.replace("_", " ")
        bhk = random.choice([1, 2, 2, 3, 3, 4])
        listing_type = random.choice([ListingTypeEnum.buy, ListingTypeEnum.buy, ListingTypeEnum.rent])

        if ptype == "plot":
            area_sqft = round(random.uniform(1200, 4800), 0)
            price_per_sqft = random.uniform(locality["min_psf"] * 0.6, locality["max_psf"] * 0.8)
            price = round((area_sqft * price_per_sqft) / 10000) * 10000
            listing_type = ListingTypeEnum.buy
            title = random.choice(plot_titles).format(city=locality["name"])
            bhk_value = None
            bathrooms_value = None
            furnishing_value = None
        else:
            area_ranges = {1: (450, 750), 2: (700, 1200), 3: (1100, 1800), 4: (1600, 2600)}
            area_sqft = round(random.uniform(*area_ranges[bhk]), 0)
            price_per_sqft = random.uniform(locality["min_psf"], locality["max_psf"])
            buy_price = round((area_sqft * price_per_sqft) / 10000) * 10000

            if listing_type == ListingTypeEnum.buy:
                price = buy_price
            else:
                price = round(buy_price * random.uniform(0.002, 0.003) / 500) * 500

            title = random.choice(titles).format(bhk=bhk, ptype=ptype_label.title(), city=locality["name"])
            bhk_value = bhk
            bathrooms_value = max(1, bhk - 1)
            furnishing_value = random.choice(furnishings)

        lat_jitter = random.uniform(-0.015, 0.015)
        lng_jitter = random.uniform(-0.015, 0.015)

        new_property = Property(
            agent_id=agent.id,
            title=title,
            description=f"A well-located {ptype_label} in {locality['name']}, Bengaluru, close to schools, hospitals, and daily conveniences.",
            property_type=PropertyTypeEnum[ptype],
            listing_type=listing_type,
            price=price,
            area_sqft=area_sqft,
            bhk=bhk_value,
            bathrooms=bathrooms_value,
            floor=None if ptype == "plot" else random.randint(0, 15),
            total_floors=None if ptype == "plot" else random.randint(4, 20),
            property_age_years=None if ptype == "plot" else random.randint(0, 15),
            furnishing=furnishing_value,
            parking=random.choice([True, True, False]),
            latitude=round(locality["lat"] + lat_jitter, 4),
            longitude=round(locality["lng"] + lng_jitter, 4),
            address=f"{random.randint(1, 200)}th Cross, {locality['name']}, Bengaluru",
            city="Bengaluru",
            status=PropertyStatusEnum.approved,
        )
        db.add(new_property)
        db.flush()

        num_images = random.randint(2, 3)
        chosen_images = random.sample(REAL_ESTATE_IMAGE_URLS, min(num_images, len(REAL_ESTATE_IMAGE_URLS)))
        for img_index, base_url in enumerate(chosen_images):
            db.add(PropertyImage(
                property_id=new_property.id,
                image_url=base_url,
                is_primary=(img_index == 0),
            ))

    db.commit()
    print("Seeded 30 realistic Bengaluru properties with real estate images successfully.")
else:
    print(f"Properties already exist ({existing_count} found) — skipping property seeding.")

db.close()