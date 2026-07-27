#!/usr/bin/env python3
"""
===============================================================================
EL MARRAQUETÓMETRO: Isocronas Peatonales de la Crujientez del Pan
-------------------------------------------------------------------------------
Modelamiento espacial de la degradación organoléptica de la marraqueta en función
del tiempo de caminata desde panaderías y almacenes en la red urbana.

Autor: Senior Spatial Data Scientist & Especialista en Analítica Urbana
Proyección predeterminada: WGS 84 / UTM Zone 19S (EPSG:32719) - Chile Central
===============================================================================
"""

import os
import sys
import logging
import geopandas as gpd
import pandas as pd
import numpy as np
import networkx as nx
import osmnx as ox
from shapely.geometry import Point, LineString, Polygon, MultiPolygon
from shapely.ops import unary_union

# Configuración de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger = logging.getLogger("Marraquetometro")

# Ajuste de configuración de OSMnx
ox.settings.use_cache = True
ox.settings.log_console = False


class MarraquetometroPipeline:
    """
    Pipeline completo de análisis espacial para calcular isocronas peatonales
    basadas en red de transporte para la accesibilidad a pan fresco.
    """

    def __init__(self, place_name="Providencia, Santiago, Chile", epsg_target=32719):
        """
        Parámetros:
        ----------
        place_name : str
            Comuna o área de estudio compatible con la API de Nominatim (OSMnx).
        epsg_target : int
            Código EPSG proyectado en metros (ej. 32719 para UTM 19S Chile).
        """
        self.place_name = place_name
        self.epsg_target = epsg_target

        # Parámetros metodológicos peatonales
        self.walking_speed_ms = 1.2  # 1.2 m/s = 4.32 km/h
        
        # Thresholds de tiempo en minutos y sus equivalentes en segundos y metros
        self.intervals_min = [3, 7, 12]
        self.intervals_sec = [t * 60 for t in self.intervals_min]
        self.intervals_meters = [t * 60 * self.walking_speed_ms for t in self.intervals_min]

        # Labels temáticos de calidad del pan
        self.quality_zones = {
            1: {"min": 0, "max": 3, "label": "0-3 min: Zona Marraqueta Crocante (Calidad Óptima)", "code": "crocante"},
            2: {"min": 3, "max": 7, "label": "3-7 min: Zona Pan Tibio (Pérdida paulatina de corteza)", "code": "tibio"},
            3: {"min": 7, "max": 12, "label": "7-12 min: Zona Goma (Requiere Tostadora)", "code": "goma"},
            4: {"min": 12, "max": 999, "label": "> 12 min: Desierto de Pan Fresco", "code": "desierto"}
        }

        self.G_proj = None
        self.gdf_pois = None
        self.isochrones_gdf = None

    def fetch_walking_network(self):
        """Descarga y proyecta el grafo de la red caminable."""
        logger.info(f"Descargando red caminable peatonal para: {self.place_name}...")
        try:
            # Filtro caminable peatonales
            G = ox.graph_from_place(
                self.place_name,
                network_type="walk",
                retain_all=False
            )
            # Proyectar a UTM (EPSG predeterminado o automático)
            self.G_proj = ox.project_graph(G, to_crs=f"EPSG:{self.epsg_target}")
            
            # Calcular travel_time (segundos) por arco (edge)
            # travel_time = length (m) / walking_speed (m/s)
            for u, v, k, data in self.G_proj.edges(keys=True, data=True):
                length = data.get("length", 0.0)
                data["travel_time"] = length / self.walking_speed_ms

            logger.info(f"Red cargada exitosamente: {len(self.G_proj.nodes)} nodos y {len(self.G_proj.edges)} arcos.")
        except Exception as e:
            logger.error(f"Error al descargar la red de OSMnx: {e}")
            raise

    def fetch_bread_pois(self):
        """Descarga puntos de interés (POIs): Panaderías y Almacenes de barrio."""
        logger.info(f"Buscando POIs de Panaderías (`shop=bakery`) y Almacenes (`shop=convenience`)...")
        tags = {
            "shop": ["bakery", "convenience"]
        }
        try:
            gdf_raw = ox.geometries_from_place(self.place_name, tags=tags)
        except AttributeError:
            # Compatibilidad con osmnx >= 1.9/2.0
            gdf_raw = ox.features_from_place(self.place_name, tags=tags)

        if gdf_raw.empty:
            raise ValueError(f"No se encontraron POIs de panadería o conveniencia en {self.place_name}")

        # Normalizar geometrías (convertir polígonos a centroides si aplica)
        gdf_clean = gdf_raw.copy()
        gdf_clean["geometry"] = gdf_clean["geometry"].centroid
        
        # Proyectar a CRS métrico
        gdf_proj = gdf_clean.to_crs(epsg=self.epsg_target)
        
        # Filtrar atributos relevantes
        gdf_proj = gdf_proj[["geometry", "shop"]].reset_index(drop=True)
        self.gdf_pois = gdf_proj
        logger.info(f"Se identificaron {len(self.gdf_pois)} POIs de pan fresco.")

    def compute_network_isochrones(self, buffer_distance=25.0, concave_alpha=None):
        """
        Calcula las isocronas peatonales basadas en el algoritmo Dijkstra Multi-Fuente
        sobre el grafo vial proyectado.
        """
        if self.G_proj is None or self.gdf_pois is None:
            raise RuntimeError("Debe ejecutar `fetch_walking_network()` y `fetch_bread_pois()` antes de calcular isocronas.")

        logger.info("Asociando POIs a los nodos más cercanos de la red vial...")
        poi_coords = [(geom.x, geom.y) for geom in self.gdf_pois.geometry]
        
        # Encontrar nodos más cercanos en la red vial proyectada
        nearest_nodes = list(set(ox.nearest_nodes(self.G_proj, X=[c[0] for c in poi_coords], Y=[c[1] for c in poi_coords])))

        logger.info("Ejecutando algoritmo de caminos mínimos Dijkstra Multi-Fuente (tiempo en segundos)...")
        
        # Dijkstra multi-fuente: calcula la menor distancia/tiempo desde CUALQUIER panadería a cada nodo
        node_distances = nx.multi_source_dijkstra_path_length(
            self.G_proj,
            sources=nearest_nodes,
            cutoff=self.intervals_sec[-1], # Máximo 12 minutos (720s)
            weight="travel_time"
        )

        # Asignar a cada nodo en el grafo su tiempo de recorrido mínimo
        for node in self.G_proj.nodes():
            if node in node_distances:
                self.G_proj.nodes[node]["time_to_bread_sec"] = node_distances[node]
                self.G_proj.nodes[node]["time_to_bread_min"] = node_distances[node] / 60.0
            else:
                self.G_proj.nodes[node]["time_to_bread_sec"] = np.inf
                self.G_proj.nodes[node]["time_to_bread_min"] = np.inf

        # Construir polígonos de isocrona para cada intervalo
        isochrone_polygons = []

        # Convertimos los nodos del grafo en un GeoDataFrame con sus atributos de tiempo
        nodes, data = zip(*self.G_proj.nodes(data=True))
        gdf_nodes = gpd.GeoDataFrame(
            list(data),
            index=nodes,
            geometry=[Point(d["x"], d["y"]) for d in data],
            crs=f"EPSG:{self.epsg_target}"
        )

        # Generar envolventes geométricas para cada umbral (acumulativo e incremental)
        previous_poly = None

        for idx, sec_limit in enumerate(self.intervals_sec, start=1):
            sub_nodes = gdf_nodes[gdf_nodes["time_to_bread_sec"] <= sec_limit]
            
            if sub_nodes.empty:
                logger.warning(f"No hay nodos alcanzables dentro de {sec_limit/60} minutos.")
                continue

            # Crear polígono buffer de la red caminable alcanzable
            # Combinar puntos de nodos y líneas de arcos dentro del umbral
            sub_edges = []
            for u, v, k, d in self.G_proj.edges(keys=True, data=True):
                u_time = self.G_proj.nodes[u].get("time_to_bread_sec", np.inf)
                v_time = self.G_proj.nodes[v].get("time_to_bread_sec", np.inf)
                if u_time <= sec_limit or v_time <= sec_limit:
                    if "geometry" in d:
                        sub_edges.append(d["geometry"])
                    else:
                        u_pt = Point(self.G_proj.nodes[u]["x"], self.G_proj.nodes[u]["y"])
                        v_pt = Point(self.G_proj.nodes[v]["x"], self.G_proj.nodes[v]["y"])
                        sub_edges.append(LineString([u_pt, v_pt]))

            # Unir geometrías de arcos y nodos
            all_geoms = list(sub_nodes.geometry) + sub_edges
            cumul_union = unary_union(all_geoms).buffer(buffer_distance)

            # Para análisis de anillos discretos (no acumulativos):
            zone_geom = cumul_union
            if previous_poly is not None:
                zone_geom = cumul_union.difference(previous_poly)

            previous_poly = cumul_union

            info = self.quality_zones[idx]
            isochrone_polygons.append({
                "zone_id": idx,
                "range_min": f"{info['min']}-{info['max']} min",
                "quality_label": info["label"],
                "code": info["code"],
                "geometry": zone_geom
            })

        self.isochrones_gdf = gpd.GeoDataFrame(isochrone_polygons, crs=f"EPSG:{self.epsg_target}")
        logger.info("Isocronas calculadas exitosamente.")

    def export_results(self, output_dir="./output"):
        """Exporta los resultados a GeoPackage y GeoJSON."""
        os.makedirs(output_dir, exist_ok=True)
        
        gpkg_path = os.path.join(output_dir, "marraquetometro_isocronas.gpkg")
        geojson_path = os.path.join(output_dir, "marraquetometro_isocronas.geojson")
        pois_path = os.path.join(output_dir, "panaderias_pois.geojson")

        logger.info(f"Guardando capa de Isocronas en GeoPackage: {gpkg_path}")
        self.isochrones_gdf.to_file(gpkg_path, layer="isocronas_crujientez", driver="GPKG")
        
        logger.info(f"Guardando capas en GeoJSON (EPSG:4326)...")
        self.isochrones_gdf.to_crs(epsg=4326).to_file(geojson_path, driver="GeoJSON")
        self.gdf_pois.to_crs(epsg=4326).to_file(pois_path, driver="GeoJSON")

        logger.info("¡Proceso finalizado con éxito! Todos los archivos fueron exportados.")


if __name__ == "__main__":
    # Ejemplo de ejecución para la comuna de Providencia, Santiago
    pipeline = MarraquetometroPipeline(place_name="Providencia, Santiago, Chile", epsg_target=32719)
    pipeline.fetch_walking_network()
    pipeline.fetch_bread_pois()
    pipeline.compute_network_isochrones(buffer_distance=30.0)
    pipeline.export_results()
