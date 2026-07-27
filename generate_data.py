#!/usr/bin/env python3
"""
===============================================================================
EL MARRAQUETÓMETRO - Generador de Datos e Isocronas con ORS API & OSM
===============================================================================
"""

import os
import json
import time
import requests
import geopandas as gpd
import pandas as pd
from shapely.geometry import shape, Point, Polygon, MultiPolygon
from shapely.ops import unary_union

ORS_API_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjcyYjk1OWVkYjZiNmI5ZWE3MGMyODBjNTBkMTVkNTcyNmUzYWE5MmQ1MDViNTIzMWVjNjg1MjcwIiwiaCI6Im11cm11cjY0In0="

# Configuración de área (Providencia - Barrio Italia / Pedro de Valdivia, Santiago)
BBOX_SANTIAGO = [-70.625, -33.435, -70.605, -33.420] # [min_lon, min_lat, max_lon, max_lat]

def fetch_pois_overpass():
    """Obtiene panaderías y almacenes de la zona via Overpass API."""
    print("--> Obteniendo POIs de Panaderías y Almacenes desde Overpass API...")
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    # Query de Overpass para Santiago / Providencia
    query = """
    [out:json][timeout:30];
    (
      node["shop"="bakery"](-33.445, -70.630, -33.415, -70.595);
      way["shop"="bakery"](-33.445, -70.630, -33.415, -70.595);
      node["shop"="convenience"](-33.445, -70.630, -33.415, -70.595);
      way["shop"="convenience"](-33.445, -70.630, -33.415, -70.595);
    );
    out center;
    """
    
    res = requests.post(overpass_url, data={"data": query})
    if res.status_code != 200:
        print(f"Error en Overpass: {res.status_code}")
        return []

    data = res.json()
    elements = data.get("elements", [])
    
    pois = []
    for el in elements:
        lon = el.get("lon") or (el.get("center", {}).get("lon"))
        lat = el.get("lat") or (el.get("center", {}).get("lat"))
        name = el.get("tags", {}).get("name", "Panadería / Almacén de Barrio")
        shop_type = el.get("tags", {}).get("shop", "bakery")
        
        if lon and lat:
            pois.append({
                "id": el.get("id"),
                "name": name,
                "shop": shop_type,
                "lon": lon,
                "lat": lat
            })
            
    print(f"--> Se obtuvieron {len(pois)} POIs en la zona de estudio.")
    return pois

def fetch_ors_isochrones(locations):
    """Calcula isocronas peatonales usando OpenRouteService API (3, 7, 12 min = 180, 420, 720 sec)."""
    print(f"--> Solicitando isocronas a OpenRouteService API para {len(locations)} puntos...")
    url = "https://api.openrouteservice.org/v2/isochrones/foot-walking"
    
    headers = {
        "Authorization": ORS_API_KEY,
        "Content-Type": "application/json"
    }

    # ORS procesa máximo 5 locations por request en versión gratuita
    all_features_3min = []
    all_features_7min = []
    all_features_12min = []

    # Agrupar en batches de 5
    batch_size = 5
    for i in range(0, min(len(locations), 15), batch_size):
        batch = locations[i:i+batch_size]
        coords = [[p["lon"], p["lat"]] for p in batch]
        
        body = {
            "locations": coords,
            "range": [180, 420, 720], # 3, 7, 12 minutos
            "range_type": "time",
            "units": "m",
            "attributes": ["area", "reachfactor"]
        }

        try:
            r = requests.post(url, json=body, headers=headers)
            if r.status_code == 200:
                resp_json = r.json()
                features = resp_json.get("features", [])
                for feat in features:
                    val = feat["properties"]["value"]
                    geom = shape(feat["geometry"])
                    if val == 180:
                        all_features_3min.append(geom)
                    elif val == 420:
                        all_features_7min.append(geom)
                    elif val == 720:
                        all_features_12min.append(geom)
            else:
                print(f"ORS API Error batch {i}: {r.status_code} - {r.text}")
        except Exception as e:
            print(f"Excepción en ORS API batch {i}: {e}")
        time.sleep(1)

    print("--> Realizando unión topológica de polígonos por zona de crujientez...")
    
    # 1. Unir polígonos acumulativos
    union_3m = unary_union(all_features_3min) if all_features_3min else Polygon()
    union_7m = unary_union(all_features_7min) if all_features_7min else Polygon()
    union_12m = unary_union(all_features_12min) if all_features_12min else Polygon()

    # 2. Generar anillos concéntricos discretos (Diferencia geométrica)
    poly_zone1 = union_3m
    poly_zone2 = union_7m.difference(union_3m)
    poly_zone3 = union_12m.difference(union_7m)

    return {
        "zone1": poly_zone1, # 0-3 min: Crocante
        "zone2": poly_zone2, # 3-7 min: Tibio
        "zone3": poly_zone3, # 7-12 min: Goma
    }

def main():
    os.makedirs("./public/data", exist_ok=True)
    
    # 1. Obtener POIs
    pois = fetch_pois_overpass()
    if not pois:
        print("No se encontraron POIs, usando muestra predeterminada de Providencia.")
        pois = [
            {"id": 1, "name": "Panadería Lo Saldes", "shop": "bakery", "lon": -70.612, "lat": -33.425},
            {"id": 2, "name": "Panadería Las Rosas Chicas", "shop": "bakery", "lon": -70.618, "lat": -33.430},
            {"id": 3, "name": "Almacén Don Pedro", "shop": "convenience", "lon": -70.615, "lat": -33.428},
            {"id": 4, "name": "Bakehouse Barrio Italia", "shop": "bakery", "lon": -70.622, "lat": -33.438},
            {"id": 5, "name": "Panadería San Antonio", "shop": "bakery", "lon": -70.608, "lat": -33.422}
        ]

    # Guardar POIs GeoJSON
    poi_features = []
    for p in pois:
        poi_features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [p["lon"], p["lat"]]
            },
            "properties": {
                "id": p["id"],
                "name": p["name"],
                "shop": p["shop"],
                "tipo_label": "Panadería Dedicada" if p["shop"] == "bakery" else "Almacén de Barrio"
            }
        })
    
    poi_geojson = {
        "type": "FeatureCollection",
        "features": poi_features
    }
    
    with open("./public/data/panaderias_pois.geojson", "w", encoding="utf-8") as f:
        json.dump(poi_geojson, f, ensure_ascii=False, indent=2)

    # 2. Obtener Isocronas desde ORS
    zones_geom = fetch_ors_isochrones(pois)
    
    # 3. Crear GeoJSON de Isocronas
    iso_features = [
        {
            "type": "Feature",
            "geometry": shape(zones_geom["zone1"]).__geo_interface__,
            "properties": {
                "zone_id": 1,
                "name": "Zona Marraqueta Crocante",
                "time_range": "0 - 3 min",
                "crispness_level": "Óptima / Crocante",
                "desc": "El pan conserva su corteza crujiente original al llegar al hogar.",
                "color": "#D84315",
                "opacity": 0.7
            }
        },
        {
            "type": "Feature",
            "geometry": shape(zones_geom["zone2"]).__geo_interface__,
            "properties": {
                "zone_id": 2,
                "name": "Zona Pan Tibio",
                "time_range": "3 - 7 min",
                "crispness_level": "Media / Comestible",
                "desc": "Empieza la pérdida gradual de corteza por vapor atrapado.",
                "color": "#FBC02D",
                "opacity": 0.6
            }
        },
        {
            "type": "Feature",
            "geometry": shape(zones_geom["zone3"]).__geo_interface__,
            "properties": {
                "zone_id": 3,
                "name": "Zona Goma",
                "time_range": "7 - 12 min",
                "crispness_level": "Baja / Tostadora Obligatoria",
                "desc": "Textura elastomérica por humedad residual. Requiere tostador.",
                "color": "#78909C",
                "opacity": 0.5
            }
        }
    ]

    iso_geojson = {
        "type": "FeatureCollection",
        "features": iso_features
    }

    with open("./public/data/marraquetometro_isocronas.geojson", "w", encoding="utf-8") as f:
        json.dump(iso_geojson, f, ensure_ascii=False, indent=2)

    print("--> ¡Archivos GeoJSON generados exitosamente en ./public/data/!")

if __name__ == "__main__":
    main()
