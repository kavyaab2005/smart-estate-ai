import time
import requests

URL = "https://overpass-api.de/api/interpreter"
HEADERS = {"User-Agent": "SmartEstateAI/1.0", "Accept": "application/json"}
LAT, LON = 12.9686, 77.7537

TESTS = {
    "A: node only, GET": ("GET", f'[out:json][timeout:25];node["amenity"="school"](around:2000,{LAT},{LON});out;'),
    "B: nwr center, GET": ("GET", f'[out:json][timeout:25];nwr["amenity"="school"](around:2000,{LAT},{LON});out center;'),
    "C: node only, POST": ("POST", f'[out:json][timeout:25];node["amenity"="school"](around:2000,{LAT},{LON});out;'),
    "D: nwr center, POST": ("POST", f'[out:json][timeout:25];nwr["amenity"="school"](around:2000,{LAT},{LON});out center;'),
}

for name, (method, query) in TESTS.items():
    start = time.time()
    try:
        if method == "GET":
            r = requests.get(URL, params={"data": query}, headers=HEADERS, timeout=40)
        else:
            r = requests.post(URL, data={"data": query}, headers=HEADERS, timeout=40)
        r.raise_for_status()
        count = len(r.json().get("elements", []))
        print(f"{name}: OK, {count} results, {time.time() - start:.1f}s")
    except Exception as e:
        print(f"{name}: FAILED after {time.time() - start:.1f}s - {str(e)[:80]}")