#!/usr/bin/env python3
"""
===============================================================================
EL MARRAQUETÓMETRO: Extracción y Generación Multirregional
(Gran Santiago, Gran Valparaíso y Gran Concepción)
===============================================================================
"""

import os
import json
import time
import requests
import geopandas as gpd
from shapely.geometry import shape, Point, Polygon, MultiPolygon
from shapely.ops import unary_union

ORS_API_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjcyYjk1OWVkYjZiNmI5ZWE3MGMyODBjNTBkMTVkNTcyNmUzYWE5MmQ1MDViNTIzMWVjNjg1MjcwIiwiaCI6Im11cm11cjY0In0="

REGIONS = {
    "gran_santiago": {
        "name": "Gran Santiago",
        "center": [-70.6506, -33.4372],
        "zoom": 11.5,
        "bbox": [-70.78, -33.60, -70.50, -33.33],
        "overpass_bbox": "(-33.60, -70.78, -33.33, -70.50)"
    },
    "gran_valparaiso": {
        "name": "Gran Valparaíso",
        "center": [-71.5518, -33.0245],
        "zoom": 12,
        "bbox": [-71.65, -33.15, -71.30, -32.90],
        "overpass_bbox": "(-33.15, -71.65, -32.90, -71.30)"
    },
    "gran_concepcion": {
        "name": "Gran Concepción",
        "center": [-73.0498, -36.8270],
        "zoom": 12,
        "bbox": [-73.18, -36.90, -72.95, -36.70],
        "overpass_bbox": "(-36.90, -73.18, -36.70, -72.95)"
    }
}

def fetch_overpass_pois(bbox_str):
    """Consulta Overpass API para extraer bakery y convenience en la BBOX."""
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json][timeout:60];
    (
      node["shop"="bakery"]{bbox_str};
      way["shop"="bakery"]{bbox_str};
      node["shop"="convenience"]{bbox_str};
      way["shop"="convenience"]{bbox_str};
    );
    out center;
    """
    try:
        res = requests.post(overpass_url, data={"data": query}, timeout=60)
        if res.status_code == 200:
            data = res.json()
            elements = data.get("elements", [])
            pois = []
            for el in elements:
                lon = el.get("lon") or (el.get("center", {}).get("lon"))
                lat = el.get("lat") or (el.get("center", {}).get("lat"))
                name = el.get("tags", {}).get("name", "Panadería / Almacén")
                shop_type = el.get("tags", {}).get("shop", "bakery")
                if lon and lat:
                    pois.append({"id": el.get("id"), "name": name, "shop": shop_type, "lon": lon, "lat": lat})
            return pois
    except Exception as e:
        print(f"Error consultando Overpass: {e}")
    return []

def compute_ors_isochrones(locations, max_pois=25):
    """Computa isocronas peatonales con ORS API."""
    url = "https://api.openrouteservice.org/v2/isochrones/foot-walking"
    headers = {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}

    # Muestrear si hay demasiados POIs para respetar cuotas de API
    sample_locs = locations[:max_pois] if len(locations) > max_pois else locations

    features_3m, features_7m, features_12m = [], [], []

    batch_size = 5
    for i in range(0, len(sample_locs), batch_size):
        batch = sample_locs[i:i+batch_size]
        coords = [[p["lon"], p["lat"]] for p in batch]
        body = {
            "locations": coords,
            "range": [180, 420, 720], # 3, 7, 12 min
            "range_type": "time"
        }

        try:
            r = requests.post(url, json=body, headers=headers)
            if r.status_code == 200:
                features = r.json().get("features", [])
                for feat in features:
                    val = feat["properties"]["value"]
                    geom = shape(feat["geometry"])
                    if val == 180: features_3m.append(geom)
                    elif val == 420: features_7m.append(geom)
                    elif val == 720: features_12m.append(geom)
            else:
                print(f"ORS Warning ({r.status_code}): {r.text[:100]}")
        except Exception as e:
            print(f"Excepción en ORS: {e}")
        time.sleep(1)

    # Unión y anillos concéntricos
    union_3m = unary_union(features_3m) if features_3m else Polygon()
    union_7m = unary_union(features_7m) if features_7m else Polygon()
    union_12m = unary_union(features_12m) if features_12m else Polygon()

    poly_zone1 = union_3m
    poly_zone2 = union_7m.difference(union_3m)
    poly_zone3 = union_12m.difference(union_7m)

    return poly_zone1, poly_zone2, poly_zone3

def process_region(region_key, info, output_dir):
    print(f"\n=======================================================")
    print(f"Procesando Región: {info['name']} ({region_key})")
    print(f"=======================================================")

    pois = fetch_overpass_pois(info["overpass_bbox"])
    print(f"--> Overpass retornó {len(pois)} POIs para {info['name']}.")

    if not pois:
        print(f"--> Generando muestra sintética distribuida para {info['name']}...")
        cx, cy = info["center"]
        pois = [
            {"id": 101, "name": f"Panadería Central {info['name']}", "shop": "bakery", "lon": cx, "lat": cy},
            {"id": 102, "name": "Almacén Don Mario", "shop": "convenience", "lon": cx + 0.008, "lat": cy + 0.005},
            {"id": 103, "name": "Panadería El Rosario", "shop": "bakery", "lon": cx - 0.007, "lat": cy - 0.006},
            {"id": 104, "name": "Bakehouse Urbano", "shop": "bakery", "lon": cx + 0.012, "lat": cy - 0.008},
            {"id": 105, "name": "Almacén La Esquina", "shop": "convenience", "lon": cx - 0.010, "lat": cy + 0.009}
        ]

    # Guardar GeoJSON POIs
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
    with open(os.path.join(output_dir, f"pois_{region_key}.geojson"), "w", encoding="utf-8") as f:
        json.dump(poi_geojson, f, ensure_ascii=False, indent=2)

    # Calcular isocronas
    z1, z2, z3 = compute_ors_isochrones(pois)

    iso_features = [
        {
            "type": "Feature",
            "geometry": shape(z1).__geo_interface__,
            "properties": {
                "zone_id": 1,
                "name": "Zona Marraqueta Crocante",
                "time_range": "0 - 3 min",
                "crispness_level": "Óptima / Crocante",
                "desc": "Corteza crujiente recién horneada.",
                "color": "#FF5722",
                "opacity": 0.7
            }
        },
        {
            "type": "Feature",
            "geometry": shape(z2).__geo_interface__,
            "properties": {
                "zone_id": 2,
                "name": "Zona Pan Tibio",
                "time_range": "3 - 7 min",
                "crispness_level": "Media / Comestible",
                "desc": "Pérdida paulatina de corteza.",
                "color": "#FFC107",
                "opacity": 0.6
            }
        },
        {
            "type": "Feature",
            "geometry": shape(z3).__geo_interface__,
            "properties": {
                "zone_id": 3,
                "name": "Zona Goma",
                "time_range": "7 - 12 min",
                "crispness_level": "Baja / Requiere Tostadora",
                "desc": "Textura elastomérica. Requiere tostador.",
                "color": "#607D8B",
                "opacity": 0.5
            }
        }
    ]

    iso_geojson = {"type": "FeatureCollection", "features": iso_features}
    with open(os.path.join(output_dir, f"isocronas_{region_key}.geojson"), "w", encoding="utf-8") as f:
        json.dump(iso_geojson, f, ensure_ascii=False, indent=2)

    print(f"--> ¡Completado {info['name']}!")

def main():
    output_dir = "./data"
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs("./public/data", exist_ok=True)

    for r_key, r_info in REGIONS.items():
        process_region(r_key, r_info, output_dir)
        process_region(r_key, r_info, "./public/data")

    # Guardar metadata
    with open(os.path.join(output_dir, "regions.json"), "w", encoding="utf-8") as f:
        json.dump(REGIONS, f, ensure_ascii=False, indent=2)

    with open(os.path.join("./public/data", "regions.json"), "w", encoding="utf-8") as f:
        json.dump(REGIONS, f, ensure_ascii=False, indent=2)

    print("\n--> ¡Procesamiento multirregional finalizado con éxito!")

if __name__ == "__main__":
    main()
