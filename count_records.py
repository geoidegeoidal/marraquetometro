import json
import glob

files = sorted(glob.glob("./data/*.geojson"))
print("=== CONTEO DE REGISTROS POR DATASET ===")
for f in files:
    with open(f, encoding="utf-8") as file:
        data = json.load(file)
        count = len(data.get("features", []))
        print(f"{f}: {count} registros")
