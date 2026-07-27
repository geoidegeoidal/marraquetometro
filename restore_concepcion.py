import os
import json
import time
import requests
from shapely.geometry import shape, Polygon
from shapely.ops import unary_union

ORS_API_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjcyYjk1OWVkYjZiNmI5ZWE3MGMyODBjNTBkMTVkNTcyNmUzYWE5MmQ1MDViNTIzMWVjNjg1MjcwIiwiaCI6Im11cm11cjY0In0="

ENDPOINTS = [
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter"
]

def get_concepcion_pois():
    query = """
    [out:json][timeout:60];
    (
      node["shop"="bakery"](-36.90, -73.18, -36.70, -72.95);
      way["shop"="bakery"](-36.90, -73.18, -36.70, -72.95);
      node["shop"="convenience"](-36.90, -73.18, -36.70, -72.95);
      way["shop"="convenience"](-36.90, -73.18, -36.70, -72.95);
    );
    out center;
    """
    for ep in ENDPOINTS:
        try:
            print(f"Probando {ep}...")
            r = requests.post(ep, data={"data": query}, timeout=30)
            if r.status_code == 200:
                data = r.json()
                pois = []
                for el in data.get("elements", []):
                    lon = el.get("lon") or (el.get("center", {}).get("lon"))
                    lat = el.get("lat") or (el.get("center", {}).get("lat"))
                    name = el.get("tags", {}).get("name", "Panadería / Almacén de Barrio")
                    shop = el.get("tags", {}).get("shop", "bakery")
                    if lon and lat:
                        pois.append({"id": el.get("id"), "name": name, "shop": shop, "lon": lon, "lat": lat})
                print(f"--> Éxito: {len(pois)} POIs obtenidos para Concepción")
                return pois
        except Exception as e:
            print(f"Error en {ep}: {e}")
    return []

def main():
    pois = get_concepcion_pois()
    if pois:
        poi_features = [{
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [p["lon"], p["lat"]]},
            "properties": {
                "id": p["id"],
                "name": p["name"],
                "shop": p["shop"],
                "tipo_label": "Panadería Dedicada" if p["shop"] == "bakery" else "Almacén de Barrio"
            }
        } for p in pois]

        poi_geojson = {"type": "FeatureCollection", "features": poi_features}

        with open("./data/pois_gran_concepcion.geojson", "w", encoding="utf-8") as f:
            json.dump(poi_geojson, f, ensure_ascii=False, indent=2)

        with open("./public/data/pois_gran_concepcion.geojson", "w", encoding="utf-8") as f:
            json.dump(poi_geojson, f, ensure_ascii=False, indent=2)

        # ORS isochrones for Gran Concepción
        url = "https://api.openrouteservice.org/v2/isochrones/foot-walking"
        headers = {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}
        sample = pois[:80]
        f3, f7, f12 = [], [], []

        for i in range(0, len(sample), 5):
            batch = sample[i:i+5]
            coords = [[p["lon"], p["lat"]] for p in batch]
            body = {"locations": coords, "range": [180, 420, 720], "range_type": "time"}
            try:
                r = requests.post(url, json=body, headers=headers, timeout=20)
                if r.status_code == 200:
                    for feat in r.json().get("features", []):
                        val = feat["properties"]["value"]
                        g = shape(feat["geometry"])
                        if val == 180: f3.append(g)
                        elif val == 420: f7.append(g)
                        elif val == 720: f12.append(g)
            except Exception:
                pass
            time.sleep(0.4)

        u3 = unary_union(f3) if f3 else Polygon()
        u7 = unary_union(f7) if f7 else Polygon()
        u12 = unary_union(f12) if f12 else Polygon()

        z1 = u3
        z2 = u7.difference(u3)
        z3 = u12.difference(u7)

        iso_features = [
            {"type": "Feature", "geometry": shape(z1).__geo_interface__, "properties": {"zone_id": 1, "name": "Zona Marraqueta Crocante", "time_range": "0 - 3 min", "crispness_level": "Óptima / Crocante", "color": "#FF5722", "opacity": 0.7}},
            {"type": "Feature", "geometry": shape(z2).__geo_interface__, "properties": {"zone_id": 2, "name": "Zona Pan Tibio", "time_range": "3 - 7 min", "crispness_level": "Media / Comestible", "color": "#FFC107", "opacity": 0.6}},
            {"type": "Feature", "geometry": shape(z3).__geo_interface__, "properties": {"zone_id": 3, "name": "Zona Goma", "time_range": "7 - 12 min", "crispness_level": "Baja / Requiere Tostadora", "color": "#607D8B", "opacity": 0.5}}
        ]

        iso_geojson = {"type": "FeatureCollection", "features": iso_features}
        with open("./data/isocronas_gran_concepcion.geojson", "w", encoding="utf-8") as f:
            json.dump(iso_geojson, f, ensure_ascii=False, indent=2)
        with open("./public/data/isocronas_gran_concepcion.geojson", "w", encoding="utf-8") as f:
            json.dump(iso_geojson, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
