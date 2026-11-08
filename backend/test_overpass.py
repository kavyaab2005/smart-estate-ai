import requests

query = """
[out:json][timeout:25];
node["amenity"="school"](around:1000,12.9758,77.6045);
out;
"""

headers = {"User-Agent": "SmartEstateAI-Test/1.0"}

for url in [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]:
    print(f"Trying {url} ...")
    try:
        r = requests.post(url, data={"data": query}, headers=headers, timeout=25)
        print("Status:", r.status_code)
        if r.status_code == 200:
            print("Success! Elements found:", len(r.json().get("elements", [])))
            break
    except Exception as e:
        print("Failed:", e)