
import json
import sys

CELL_SIZE = 16      # separación entre sub-zonas en el layout general
UNIT = 1.4           # separación entre pasillos/posiciones/niveles dentro de una sub-zona


def construir_layout(dataset: dict) -> dict:
    subzonas_orden = list(dataset["resumen_por_subzona"].keys())
    # grilla de 4 columnas para acomodar las sub-zonas
    n_cols = 4
    origenes = {}
    for i, key in enumerate(subzonas_orden):
        col = i % n_cols
        row = i // n_cols
        origenes[key] = (col * CELL_SIZE, row * CELL_SIZE)

    for sku in dataset["skus"]:
        key = f"{sku['zona_excel']} / {sku['subzona']}"
        ox, oz = origenes.get(key, (0, 0))
        sku["world_x"] = round(ox + sku["pasillo_x"] * UNIT, 2)
        sku["world_z"] = round(oz + sku["posicion_y"] * UNIT, 2)
        sku["world_y"] = round(sku["nivel_z"] * UNIT, 2)

    dataset["layout_subzonas"] = [
        {"subzona": key, "origen_x": ox, "origen_z": oz}
        for key, (ox, oz) in origenes.items()
    ]
    return dataset


if __name__ == "__main__":
    path_in = sys.argv[1] if len(sys.argv) > 1 else "digital_twin_data.json"
    path_out = sys.argv[2] if len(sys.argv) > 2 else "digital_twin_world.json"

    dataset = json.load(open(path_in, encoding="utf-8"))
    dataset = construir_layout(dataset)

    with open(path_out, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False, default=str)

    print(f"Exportado: {path_out}")
