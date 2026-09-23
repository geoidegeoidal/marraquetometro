# 🥖 El Marraquetómetro 🇨🇱

### *Modelamiento Espacial e Isocronas Peatonales de la Crujientez del Pan Fresco en Chile*

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![Geospatial](https://img.shields.io/badge/GeoPandas-OSMnx-green?style=for-the-badge&logo=qgis)
![MapLibre](https://img.shields.io/badge/MapLibre_GL-Interactive_Map-orange?style=for-the-badge&logo=mapbox)
![License](https://img.shields.io/badge/License-MIT-purple?style=for-the-badge)

> **"¿Cuántos minutos soporta el pan crujiente antes de convertirse en goma durante la caminata a casa?"**

**El Marraquetómetro** es una plataforma de analítica espacial urbana que modela la accesibilidad peatonal a panaderías y almacenes de barrio en las principales áreas metropolitanas de Chile (**Gran Santiago**, **Gran Valparaíso** y **Gran Concepción**).

Mediante análisis de redes viales topológicas (OSMnx / NetworkX) y algoritmos de isocronas dinámicas, el sistema evalúa el gradiente de degradación organoléptica del pan recién horneado (especialmente la icónica **Marraqueta / Pan Francés / Pan Batido**) desde el punto de venta hasta el hogar.

---

> **Estado: prototipo experimental.** El modelo de “crujientez” es una exploración lúdica, no una medición física validada ni una recomendación de consumo.

## 🌟 Características Principales

- 🗺️ **Visualizador Interactivo Next-Gen**: Mapa web vectorizado con **MapLibre GL JS**, diseño *Dark Glassmorphism*, renderizado suave de isocronas poligonales y marcadores interactivos.
- 🇨🇱 **Cobertura Tri-Regional**:
  - **Gran Santiago** (Providencia, Las Condes, Santiago Centro, Ñuñoa, etc.)
  - **Gran Valparaíso** (Valparaíso, Viña del Mar, Concón)
  - **Gran Concepción** (Concepción, San Pedro de la Paz, Talcahuano)
- 🚶 **Isocronas Basadas en Red Real**: Cálculo por rastro de red peatonal ($v = 1.2\text{ m/s}$) superando los búferes euclidianos simples.
- 🎯 **Geolocalización & Búsqueda Nominatim**: Encuentra la calidad esperada de tu marraqueta desde cualquier dirección o tu ubicación GPS en tiempo real.
- 📊 **Métricas de Cobertura Espacial**: Panel analítico dinámico con cálculo de superficie cubierta ($\text{km}^2$) por categoría de frescura.

---

## 🥖 Escala Científica de Crujientez

El modelo categoriza el territorio urbano según el tiempo de traslado peatonal desde la panadería más cercana:

| Nivel de Frescura | Tiempo | Color UI | Descripción Organoléptica |
| :--- | :--- | :--- | :--- |
| **Crocante y Calientito** | $\le 3\text{ min}$ | 🔴 `#FF5722` | Pan recién salidito del horno. Corteza crujiente perfecta y miga esponjosa. |
| **Tibio Aceptable** | $3 - 7\text{ min}$ | 🟡 `#FFC107` | El pan se está enfriando. Mantiene buena textura, apto para mantequilla derretida. |
| **Pan Goma** | $7 - 12\text{ min}$ | 🔵 `#607D8B` | Pérdida progresiva de crujientez debido a la condensación de vapor de agua. |
| **Desierto del Pan** | $> 12\text{ min}$ | ⬛ `#334155` | Zona de sombra peatonal. Requiere recalentado o consumo tostado. |

---

## 🛠️ Arquitectura y Tecnologías

### **Backend / Pipeline Espacial**
- **Python 3.10+**
- **[OSMnx](https://osmnx.readthedocs.io/) & [NetworkX](https://networkx.org/)**: Extracción de grafos viales desde OpenStreetMap y cálculo de árbol de caminos mínimos (Dijkstra).
- **[GeoPandas](https://geopandas.org/) & [Shapely](https://shapely.readthedocs.io/)**: Proyección cartesiana UTM Zone 19S (EPSG:32719), generación de envolventes cóncavas (*concave hulls*) y unión disuelta de isocronas.
- **OpenStreetMap / Overpass API**: Extracción masiva de POIs (`shop=bakery`, `shop=convenience`).

### **Frontend / Mapa Interactivo**
- **[MapLibre GL JS](https://maplibre.org/)**: Motor de mapas vectorial de alto rendimiento.
- **[Turf.js](https://turfjs.org/)**: Análisis espacial *in-browser* para detección de contención punto-en-polígono.
- **Google Fonts (Outfit & Inter)** + **Lucide Icons**: Tipografía y microinteracciones de nivel profesional.

---

## 🚀 Inicio Rápido

### 1. Clonar el repositorio
```bash
git clone https://github.com/geoidegeoidal/marraquetometro.git
cd marraquetometro
```

### 2. Instalar dependencias de Python
```bash
pip install -r requirements.txt
```

### 3. Generar / Actualizar datos de Isocronas
```bash
# Procesa el grafo vial y POIs para las regiones
python download_all_regions.py
```

### 4. Iniciar el Servidor Web Local
```bash
python -m http.server 8080
```
Abre en tu navegador: [http://localhost:8080](http://localhost:8080)

---

## 📁 Estructura del Proyecto

```
marraquetometro/
├── data/                       # GeoJSONs compilados de isocronas y POIs
│   ├── isocronas_gran_santiago.geojson
│   ├── isocronas_gran_valparaiso.geojson
│   ├── isocronas_gran_concepcion.geojson
│   └── regions.json
├── public/                     # Archivos estáticos accesibles por la app
├── index.html                  # Aplicación Web e Interfaz de MapLibre GL
├── marraquetometro.py          # Clase principal del Pipeline Espacial
├── download_all_regions.py     # Script de descarga y procesamiento multirregional
├── fetch_all_pois.py           # Extractor de POIs vía Overpass API
├── generate_data.py            # Generador alternativo vía OpenRouteService API
├── requirements.txt            # Dependencias Python
├── .gitignore                  # Exclusiones de control de versiones
└── README.md                   # Documentación del proyecto
```

---

## 📄 Licencia

Este proyecto está bajo la Licencia **MIT** — puedes usarlo, modificarlo y compartirlo libremente.

---

<p align="center">
  Hecho con 🥖, ☕ y 🗺️ para la comunidad de Ciencia de Datos Espaciales en Chile.
</p>

