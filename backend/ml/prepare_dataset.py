import pandas as pd
import numpy as np
import os

np.random.seed(42)
N = 250

areas = [
    "Whitefield", "Koramangala", "Indiranagar", "HSR Layout", "Marathahalli",
    "Electronic City", "Jayanagar", "Bannerghatta Road", "Hebbal", "JP Nagar",
    "Yelahanka", "Sarjapur Road", "Bellandur", "Banashankari", "BTM Layout",
    "Rajajinagar", "Basavanagudi", "Malleswaram", "Vijayanagar", "Hennur"
]

area_price = {
    "Whitefield": 6500, "Koramangala": 9500, "Indiranagar": 11000,
    "HSR Layout": 8500, "Marathahalli": 6000, "Electronic City": 5000,
    "Jayanagar": 10000, "Bannerghatta Road": 5500, "Hebbal": 7500,
    "JP Nagar": 7000, "Yelahanka": 5000, "Sarjapur Road": 6000,
    "Bellandur": 7000, "Banashankari": 8000, "BTM Layout": 7500,
    "Rajajinagar": 8500, "Basavanagudi": 9000, "Malleswaram": 10000,
    "Vijayanagar": 7000, "Hennur": 5500
}

prop_types  = ["apartment", "villa", "house", "plot"]
listings    = ["sale", "rent"]
furnishings = ["furnished", "semi-furnished", "unfurnished"]
amenities_pool = ["gym", "swimming pool", "parking", "security", "garden",
                  "clubhouse", "power backup", "lift"]

rows = []
for _ in range(N):
    area  = np.random.choice(areas)
    ptype = np.random.choice(prop_types, p=[0.6, 0.15, 0.15, 0.1])
    ltype = np.random.choice(listings,   p=[0.7, 0.3])
    bhk   = int(np.random.choice([1, 2, 3, 4], p=[0.15, 0.4, 0.35, 0.1]))
    sqft  = int(np.random.randint(400, 4000))
    fl    = int(np.random.randint(0, 15))
    totfl = int(max(fl, np.random.randint(fl, 20)))
    age   = int(np.random.randint(0, 25))
    furn  = np.random.choice(furnishings)
    park  = int(np.random.randint(0, 3))
    n_am  = int(np.random.randint(1, 6))
    amen  = list(np.random.choice(amenities_pool, n_am, replace=False))

    base = area_price[area] * sqft
    if ptype == "villa":       base *= 1.3
    if ptype == "plot":        base *= 0.7
    if furn == "furnished":    base *= 1.1
    if furn == "unfurnished":  base *= 0.9
    if ltype == "rent":        base *= 0.003
    base *= (1 + np.random.uniform(-0.15, 0.15))
    price = round(base, -3)

    title = f"{bhk} BHK {ptype.title()} for {ltype.title()} in {area}"
    desc  = (f"Beautiful {bhk} BHK {ptype} for {ltype} in {area}, Bangalore. "
             f"Area: {sqft} sqft. {furn.title()}. Floor {fl}/{totfl}. "
             f"Age: {age} yrs. Amenities: {', '.join(amen)}.")

    rows.append({
        "property_type": ptype, "listing_type": ltype, "price": price,
        "area_sqft": sqft, "bhk": bhk, "bedrooms": bhk,
        "floor": fl, "total_floors": totfl, "property_age_years": age,
        "furnishing": furn, "parking": park, "city": area,
        "amenities": "|".join(amen), "title": title, "description": desc
    })

df = pd.DataFrame(rows)
out_dir = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "bangalore_properties.csv")
df.to_csv(out_path, index=False)
print(f"Dataset saved to {out_path}")
print(f"Shape: {df.shape}")
print(f"Price range: Rs.{df['price'].min():,.0f} to Rs.{df['price'].max():,.0f}")