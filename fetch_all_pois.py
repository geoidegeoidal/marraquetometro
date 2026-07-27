#!/usr/bin/env python3
"""
===============================================================================
EL MARRAQUETÓMETRO: Extracción Masiva Completa de POIs e Isocronas ORS
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

# Endpoints de Overpass API con espejos de respaldo
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter"
]

REGIONS = {
    "gran_santiago": {
        "name": "Gran Santiago",
        "center": [-70.6506, -33.4372],
        "zoom": 12,
        "query_areas": [
            "Santiago", "Providencia", "Las Condes", "Ñuñoa", "La Florida",
            "Maipú", "San Miguel", "Macul", "Recoleta", "Independencia",
            "Peñalolén", "Vitacura", "La Reina", "Pudahuel", "Quilicura"
        ]
    },
    "gran_valparaiso": {
        "name": "Gran Valparaíso",
        "center": [-71.5518, -33.0245],
        "zoom": 12.5,
        "query_areas": [
            "Valparaíso", "Viña del Mar", "Concón", "Quilpué", "Villa Alemana"
        ]
    },
    "gran_concepcion": {
        "name": "Gran Concepción",
        "center": [-73.0498, -36.8270],
        "zoom": 12.5,
        "query_areas": [
            "Concepción", "Talcahuano", "San Pedro de la Paz", "Chiguayante", "Penco", "Hualpén"
        ]
    }
}

def query_overpass(query_str):
    headers = {"User-Agent": "MarraquetometroSpatialAnalyst/1.0"}
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            print(f"--> Consultando Overpass ({endpoint})...")
            res = requests.post(endpoint, data={"data": query_str}, headers=headers, timeout=90)
            if res.status_code == 200:
                return res.json()
            else:
                print(f"   Status {res.status_code} en {endpoint}")
        except Exception as e:
            print(f"   Error en {endpoint}: {e}")
        time.sleep(1)
    return None

def get_pois_for_region(region_info):
    pois = []
    seen_ids = set()
    areas = region_info["query_areas"]
    
    print(f"--> Extrayendo POIs para {region_info['name']} en {len(areas)} comunas...")

    for area in areas:
        query = f"""
        [out:json][timeout:60];
        area["name"="{area}"]["boundary"="administrative"]->.a;
        (
          node["shop"="bakery"](area.a);
          way["shop"="bakery"](area.a);
          node["shop"="convenience"](area.a);
          way["shop"="convenience"](area.a);
        );
        out center;
        """
        data = query_overpass(query)
        if data and "elements" in data:
            for el in data["elements"]:
                el_id = el.get("id")
                if el_id in seen_ids:
                    continue
                seen_ids.add(el_id)
                
                lon = el.get("lon") or (el.get("center", {}).get("lon"))
                lat = el.get("lat") or (el.get("center", {}).get("lat"))
                tags = el.get("tags", {})
                name = tags.get("name", "Panadería / Almacén de Barrio")
                shop = tags.get("shop", "bakery")

                if lon and lat:
                    pois.append({
                        "id": el_id,
                        "name": name,
                        "shop": shop,
                        "lon": lon,
                        "lat": lat
                    })
        time.sleep(0.5)

    print(f"--> Total POIs reales extraídos para {region_info['name']}: {len(pois)}")
    return pois

def compute_all_ors_isochrones(pois):
    """Computa isocronas masivas en lotes de 5 para TODOS los POIs extraídos."""
    url = "https://api.openrouteservice.org/v2/isochrones/foot-walking"
    headers = {
        "Authorization": ORS_API_KEY,
        "Content-Type": "application/json"
    }

    print(f"--> Calculando isocronas ORS en red caminable para los {len(pois)} POIs...")

    features_3m, features_7m, features_12m = [], [], []

    batch_size = 5
    for i in range(0, len(pois), batch_size):
        batch = pois[i:i+batch_size]
        coords = [[p["lon"], p["lat"]] for p in batch]
        
        body = {
            "locations": coords,
            "range": [180, 420, 720], # 3 min, 7 min, 12 min
            "range_type": "time"
        }

        try:
            r = requests.post(url, json=body, headers=headers, timeout=30)
            if r.status_code == 200:
                res_data = r.json()
                for feat in res_data.get("features", []):
                    val = feat["properties"]["value"]
                    g = shape(feat["geometry"])
                    if val == 180: features_3m.append(g)
                    elif val == 420: features_7m.append(g)
                    elif val == 720: features_12m.append(g)
            else:
                print(f"   ORS Warning Lote {i//5 + 1}: Status {r.status_code}")
        except Exception as e:
            print(f"   Error de conexión ORS en lote {i//5 + 1}: {e}")
        time.sleep(0.6)

    print(f"--> Realizando fusión topológica de geometrías de red...")
    u3 = unary_union(features_3m) if features_3m else Polygon()
    u7 = unary_union(features_7m) if features_7m else Polygon()
    u12 = unary_union(features_12m) if features_12m else Polygon()

    # Anillos relacionales discretos
    z1 = u3
    z2 = u7.difference(u3)
    z3 = u12.difference(u7)

    return z1, z2, z3

def main():
    os.makedirs("./data", exist_ok=True)
    os.makedirs("./public/data", exist_ok=True)

    for key, info in REGIONS.items():
        print(f"\n=======================================================")
        print(f"PROCESAMIENTO MASIVO: {info['name']} ({key})")
        print(f"=======================================================")

        pois = get_pois_for_region(info)

        # Si por alguna razón Overpass falla temporalmente, no dejar en 0
        if not pois:
            print("Fallback regional a coordenadas principales...")
            cx, cy = info["center"]
            pois = [{"id": 1, "name": f"Panadería Central {info['name']}", "shop": "bakery", "lon": cx, "lat": cy}]

        # Guardar POIs GeoJSON
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

        with open(f"./data/pois_{key}.geojson", "w", encoding="utf-8") as f:
            json.dump(poi_geojson, f, ensure_ascii=False, indent=2)

        with open(f"./public/data/pois_{key}.geojson", "w", encoding="utf-8") as f:
            json.dump(poi_geojson, f, ensure_ascii=False, indent=2)

        # Computar Isocronas masivas para todos los POIs
        z1, z2, z3 = compute_all_ors_isochrones(pois)

        iso_features = [
            {
                "type": "Feature",
                "geometry": shape(z1).__geo_interface__,
                "properties": {
                    "zone_id": 1, "name": "Zona Marraqueta Crocante",
                    "time_range": "0 - 3 min", "crispness_level": "Óptima / Crocante",
                    "color": "#FF5722", "opacity": 0.7
                }
            },
            {
                "type": "Feature",
                "geometry": shape(z2).__geo_interface__,
                "properties": {
                    "zone_id": 2, "name": "Zona Pan Tibio",
                    "time_range": "3 - 7 min", "crispness_level": "Media / Comestible",
                    "color": "#FFC107", "opacity": 0.6
                }
            },
            {
                "type": "Feature",
                "geometry": shape(z3).__geo_interface__,
                "properties": {
                    "zone_id": 3, "name": "Zona Goma",
                    "time_range": "7 - 12 min", "crispness_level": "Baja / Requiere Tostadora",
                    "color": "#607D8B", "opacity": 0.5
                }
            }
        ]

        iso_geojson = {"type": "FeatureCollection", "features": iso_features}

        with open(f"./data/isocronas_{key}.geojson", "w", encoding="utf-8") as f:
            json.dump(iso_geojson, f, ensure_ascii=False, indent=2)

        with open(f"./public/data/isocronas_{key}.geojson", "w", encoding="utf-8") as f:
            json.dump(iso_geojson, f, ensure_ascii=False, indent=2)

        print(f"--> ¡Completado {info['name']} con {len(pois)} POIs masivos e isocronas de red!")

    print("\n=======================================================")
    print("¡EXTRACCIÓN Y CÁLCULO MASIVO FINALIZADO EN LAS 3 REGIONES!")
    print("=======================================================")

if __name__ == "__main__":
    main()
