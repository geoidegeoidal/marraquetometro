# 🥖 El Marraquetómetro 🇨🇱

### *Accesibilidad a panaderías y una exploración lúdica del pan fresco en Chile*

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![Geospatial](https://img.shields.io/badge/GeoPandas-OSMnx-green?style=for-the-badge&logo=qgis)
![MapLibre](https://img.shields.io/badge/MapLibre_GL-Interactive_Map-orange?style=for-the-badge&logo=mapbox)
![License](https://img.shields.io/badge/License-MIT-purple?style=for-the-badge)

> **"¿Cuántos minutos soporta el pan crujiente antes de convertirse en goma durante la caminata a casa?"**

**El Marraquetómetro** explora la accesibilidad a panaderías y almacenes de barrio en **Gran Santiago**, **Gran Valparaíso** y **Gran Concepción** mediante un visor de isocronas precalculadas.

La **marraqueta / pan francés / pan batido** sirve como hilo narrativo para leer tiempos de traslado; el visor no mide la temperatura, textura ni calidad real del pan.

[Ver el mapa localmente](#inicio-rápido) · [Escala lúdica](#escala-lúdica-de-crujientez) · [Regenerar datos](#regenerar-datos-opcional)

---

> **Estado: prototipo experimental.** El modelo de “crujientez” es una exploración lúdica, no una medición física validada ni una recomendación de consumo.

## Qué incluye

| Componente | Qué permite |
|---|---|
| Mapa MapLibre GL JS | Explorar las capas GeoJSON incluidas con una interfaz oscura. |
| Selector regional | Cambiar entre Gran Santiago, Gran Valparaíso y Gran Concepción. |
| Puntos de interés | Consultar panaderías y almacenes del conjunto cargado. |
| Inspección por clic | Consultar la zona del mapa y una estimación orientativa de minutos. |
| Scripts Python | Descargar o regenerar datos mediante distintos flujos geoespaciales. |

> El tiempo mostrado al inspeccionar un punto se calcula con la distancia geodésica al POI más cercano y una velocidad de 1,2 m/s. No es una ruta peatonal calculada en ese momento ni debe confundirse con las isocronas precalculadas.

---

## Escala lúdica de crujientez

Las categorías representan intervalos de tiempo con nombres humorísticos. Las descripciones de textura son parte de la narrativa, no resultados de una validación física:

| Nivel de Frescura | Tiempo | Color UI | Descripción Lúdica |
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

## Inicio rápido

### 1. Clonar el repositorio
```bash
git clone https://github.com/geoidegeoidal/marraquetometro.git
cd marraquetometro
```

### 2. Abrir el visor con los datos incluidos

No necesitas instalar las dependencias geoespaciales ni regenerar datos para esta primera consulta. Con Python disponible:

```bash
python -m http.server 8080
```

Abre [http://localhost:8080](http://localhost:8080) y selecciona una región. El visor carga los archivos de [`data/`](data/).

**Necesita conexión:** las bibliotecas, fuentes y el mapa base se cargan desde servicios externos. Servir los GeoJSON localmente no convierte toda la aplicación en una solución offline.

## Regenerar datos (opcional)

Este paso es distinto de consultar el mapa y puede sobrescribir archivos de `data/` y `public/data/`. Conserva una copia de los resultados que quieras mantener.

```bash
python -m pip install -r requirements.txt
```

El flujo de [`download_all_regions.py`](download_all_regions.py) consulta **Overpass** para los POI y **OpenRouteService** para las isocronas. Los ocho generadores que usan ORS leen `ORS_API_KEY` del entorno mediante [`ors_config.py`](ors_config.py). Si falta o está vacía, se detienen antes de consultar servicios o escribir datos. Las cuotas y disponibilidad de los servicios pueden limitar los resultados.

Introduce una **clave nueva** sin guardarla en el historial de comandos:

```bash
# Bash: la entrada no se muestra en pantalla
read -rsp 'ORS API key: ' ORS_API_KEY; echo
export ORS_API_KEY
python download_all_regions.py
unset ORS_API_KEY
```

```powershell
# PowerShell 7+: la entrada no se muestra en pantalla
$env:ORS_API_KEY = Read-Host 'ORS API key' -MaskInput
python download_all_regions.py
Remove-Item Env:ORS_API_KEY
```

[` .env.example`](.env.example) es solo una plantilla vacía: **los scripts no cargan archivos `.env` automáticamente**. `.env` y sus variantes se excluyen de Git, pero eso no protege claves escritas en código, HTML, GeoJSON o logs. El visor y el pipeline OSMnx de `marraquetometro.py` no necesitan esta variable.

### Prevención de filtraciones

Instala el hook en **cada clon** antes de trabajar (requiere acceso a la red la primera vez):

```bash
python -m pip install pre-commit
pre-commit install
pre-commit run --all-files
```

El hook utiliza Gitleaks fijado a una revisión concreta. El workflow **Credential safety** comprueba archivos actuales y commits nuevos con resultados redactados; no utiliza la clave ORS ni consulta su API. Conserva las reglas generales de Gitleaks y añade detección específica de ORS.

Para comprobar localmente la configuración sin red: `python -m unittest discover -s tests -v`. Los tests de integración del escáner necesitan Gitleaks instalado o `GITLEAKS_BIN` apuntando a su ejecutable; CI lo proporciona y ejecuta toda la suite.

**Límites:** un hook local puede omitirse y CI se ejecuta después de publicar. Activa además [push protection](https://docs.github.com/en/code-security/how-tos/secure-your-secrets/prevent-future-leaks/enable-push-protection) y exige el check `security` para fusionar, cuando tu configuración de GitHub lo permita. Ningún escáner garantiza detectar todos los formatos de clave.

**Incidente anterior:** una clave ORS estuvo publicada y sigue accesible en el historial. Su propietario debe revocarla en OpenRouteService y crear otra; eliminarla del código no la invalida. No reutilices la anterior ni la pegues en issues, PR o chats. Este cambio no reescribe el historial ni certifica que la revocación ya ocurrió.

**Límites de este generador:**
- Si Overpass no devuelve POI, el script crea una muestra sintética. No debe interpretarse como un catastro verificado de comercios.
- La consulta de isocronas usa como máximo los primeros 25 POI por región.
- Los archivos pueden quedar incompletos si fallan las consultas externas; revisa los mensajes y resultados antes de publicarlos.

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

