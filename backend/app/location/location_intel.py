import time
import requests
from geopy.distance import geodesic
from sqlalchemy.orm import Session
from app.models.common import LocationCache
from datetime import datetime, timedelta

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]

CATEGORY_TAGS = {
    "schools": '["amenity"="school"]',
    "colleges": '["amenity"="university"]',
    "hospitals": '["amenity"="hospital"]',
    "metro": '["railway"="station"]',
    "bus_stops": '["highway"="bus_stop"]',
    "malls": '["shop"="mall"]',
    "restaurants": '["amenity"="restaurant"]',
    "parks": '["leisure"="park"]',
}

SEARCH_RADIUS_METERS = 2000
CACHE_TTL_HOURS = 24
REQUEST_TIMEOUT_SECONDS = 30


def build_query(lat, lon, tag_filter):
    return f"[out:json][timeout:25];nwr{tag_filter}(around:{SEARCH_RADIUS_METERS},{lat},{lon});out center;"


def fetch_category(lat, lon, category, dead_mirrors):
    tag_filter = CATEGORY_TAGS[category]
    query = build_query(lat, lon, tag_filter)

    headers = {
        "User-Agent": "SmartEstateAI/1.0",
        "Accept": "application/json",
    }

    candidates = [u for u in OVERPASS_URLS if u not in dead_mirrors]

    for url in candidates:
        try:
            response = requests.post(url, data={"data": query}, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            data = response.json()
            break
        except Exception as e:
            print(f"  Overpass mirror {url} failed for {category}: {e}")
            if isinstance(e, requests.exceptions.ConnectionError):
                dead_mirrors.add(url)
            continue
    else:
        return None

    results = []
    origin = (lat, lon)

    for element in data.get("elements", []):
        name = element.get("tags", {}).get("name", f"Unnamed {category[:-1]}")

        if element["type"] == "node":
            point = (element["lat"], element["lon"])
        elif "center" in element:
            point = (element["center"]["lat"], element["center"]["lon"])
        else:
            continue

        distance_km = round(geodesic(origin, point).km, 2)
        results.append({"name": name, "distance_km": distance_km})

    results.sort(key=lambda x: x["distance_km"])
    return results[:3]

CATEGORY_MATCH = {
    "schools": ("amenity", "school"),
    "colleges": ("amenity", "university"),
    "hospitals": ("amenity", "hospital"),
    "metro": ("railway", "station"),
    "bus_stops": ("highway", "bus_stop"),
    "malls": ("shop", "mall"),
    "restaurants": ("amenity", "restaurant"),
    "parks": ("leisure", "park"),
}


def fetch_all_categories(lat, lon):
    """One Overpass request for every category. Returns a dict, or None if all mirrors fail."""
    parts = "".join(
        f'nwr["{k}"="{v}"](around:{SEARCH_RADIUS_METERS},{lat},{lon});'
        for k, v in CATEGORY_MATCH.values()
    )
    query = f"[out:json][timeout:60];({parts});out center;"
    headers = {"User-Agent": "SmartEstateAI/1.0", "Accept": "application/json"}

    data = None
    for url in dict.fromkeys(OVERPASS_URLS):
        try:
            response = requests.post(url, data={"data": query}, headers=headers, timeout=(10, 70))
            response.raise_for_status()
            data = response.json()
            break
        except Exception as e:
            print(f"  Overpass mirror {url} failed: {e}")
            continue

    if data is None:
        return None

    origin = (lat, lon)
    nearby = {category: [] for category in CATEGORY_MATCH}

    for element in data.get("elements", []):
        tags = element.get("tags", {})
        if "lat" in element:
            point = (element["lat"], element["lon"])
        elif "center" in element:
            point = (element["center"]["lat"], element["center"]["lon"])
        else:
            continue

        distance_km = round(geodesic(origin, point).km, 2)
        for category, (key, value) in CATEGORY_MATCH.items():
            if tags.get(key) == value:
                name = tags.get("name", f"Unnamed {category[:-1]}")
                nearby[category].append({"name": name, "distance_km": distance_km})

    for category in nearby:
        nearby[category].sort(key=lambda x: x["distance_km"])
        nearby[category] = nearby[category][:3]

    return nearby

def get_cached_location(db: Session, property_id: str):
    cache = db.query(LocationCache).filter(LocationCache.property_id == property_id).first()
    if not cache:
        return None
    
    if datetime.utcnow() - cache.updated_at > timedelta(hours=CACHE_TTL_HOURS):
        return None
    
    return {
        "nearby": cache.nearby_json,
        "location_score": cache.location_score,
        "data_source": cache.data_source,
    }


def save_location_cache(db: Session, property_id: str, nearby, location_score, data_source):
    cache = db.query(LocationCache).filter(LocationCache.property_id == property_id).first()
    if cache:
        cache.nearby_json = nearby
        cache.location_score = location_score
        cache.data_source = data_source
        cache.updated_at = datetime.utcnow()
    else:
        cache = LocationCache(
            property_id=property_id,
            nearby_json=nearby,
            location_score=location_score,
            data_source=data_source,
        )
        db.add(cache)
    db.commit()


def get_nearby_facilities(db: Session, lat, lon, property_id: str, city: str = ""):
    cached = get_cached_location(db, property_id)
    if cached:
        return cached, True

    used_fallback = False

    nearby = fetch_all_categories(lat, lon)
    if nearby is None:
        print("Warning: all Overpass mirrors failed")
        nearby = {category: [] for category in CATEGORY_TAGS}
        used_fallback = True

    location_score = compute_location_score(nearby)
    
    # Determine data source based on what succeeded
    data_source = "unavailable" if used_fallback else "live"
    
    # Only cache when every category was fetched successfully
    if not used_fallback:
        save_location_cache(db, property_id, nearby, location_score, data_source)
    
    return {
        "nearby": nearby,
        "location_score": location_score,
        "data_source": data_source,
    }, False


def compute_location_score(nearby):
    score = 0
    max_per_category = 100 / len(CATEGORY_TAGS)

    for category, places in nearby.items():
        if not places:
            continue

        count_score = min(len(places), 3) / 3

        closest_distance = places[0]["distance_km"]
        proximity_score = max(0, 1 - (closest_distance / 2.0))

        category_score = max_per_category * (0.5 * count_score + 0.5 * proximity_score)
        score += category_score

    return round(min(score, 100))


def get_location_intel(db: Session, lat, lon, property_id: str, city: str = ""):
    result, from_cache = get_nearby_facilities(db, lat, lon, property_id, city)
    result["from_cache"] = from_cache
    return result


if __name__ == "__main__":
    from app.database import get_db
    db = next(get_db())
    result = get_location_intel(db, 12.9758, 77.6045, "11111111-1111-1111-1111-111111111111", city="Bengaluru")
    for category, places in result["nearby"].items():
        print(f"{category}: {len(places)} found, closest: {places[0] if places else 'none'}")
    print("Location score:", result["location_score"])
    print("Data source:", result["data_source"])
    print("From cache:", result["from_cache"])