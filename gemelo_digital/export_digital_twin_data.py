
import json
import sys

import openpyxl

from assign_slots import ZoneAssigner


def cargar_analytics_base(path_excel: str) -> list[dict]:
    wb = openpyxl.load_workbook(path_excel, data_only=True)
    ws = wb["ANALYTICS_BASE"]
    rows = list(ws.iter_rows(values_only=True))

    data = []
    # Las filas de datos empiezan en el índice 4 (fila 5 de Excel)
    for r in rows[4:]:
        if r[0] is None:
            continue
        (sku, marca, familia, rot, abc, zona, tiempo_acc, dist, vol,
         peso, minpick, zona_lejana, candidato) = r[0:13]
        data.append(dict(
            sku=sku, marca=marca, familia=familia, rotacion_6m=rot, abc=abc,
            zona_excel=zona, tiempo_acceso_min=tiempo_acc, distancia_m=dist,
            volumen_m3=vol, peso_kg=peso, min_pick_anualiz=minpick,
            zona_lejana=zona_lejana, candidato_reslotting=candidato,
        ))
    return data


def calcular_color_heat(heat: float, heat_min: float, heat_max: float) -> str:
    """Clasifica el valor de heat en 3 buckets (bajo/medio/alto) usando
    terciles del rango observado. Devuelve un color hex fijo por bucket
    -- reemplazar por escala continua si se quiere más granularidad."""
    if heat_max == heat_min:
        return "#97C459"  # verde por defecto si no hay variación
    ratio = (heat - heat_min) / (heat_max - heat_min)
    if ratio < 0.33:
        return "#97C459"  # verde - bajo
    elif ratio < 0.66:
        return "#FAC775"  # ámbar - medio
    else:
        return "#F09595"  # rojo - alto


def construir_dataset(path_excel: str) -> dict:
    filas = cargar_analytics_base(path_excel)
    assigner = ZoneAssigner()

    registros = []
    for fila in filas:
        asignacion = assigner.asignar(fila["sku"], fila["zona_excel"])
        heat = round(fila["min_pick_anualiz"] * asignacion.multiplicador_tiempo, 1)
        registros.append({
            **fila,
            "subzona": asignacion.subzona,
            "pasillo_x": asignacion.pasillo,
            "posicion_y": asignacion.posicion,
            "nivel_z": asignacion.nivel,
            "operacion": asignacion.operacion,
            "requiere_grua": asignacion.requiere_grua,
            "heat_tiempo_picking": heat,
        })

    heats = [r["heat_tiempo_picking"] for r in registros]
    heat_min, heat_max = min(heats), max(heats)
    for r in registros:
        r["color_heat"] = calcular_color_heat(r["heat_tiempo_picking"], heat_min, heat_max)

    return {
        "meta": {
            "total_skus": len(registros),
            "heat_min": heat_min,
            "heat_max": heat_max,
            "cobertura_almacen": "~1% (muestra académica de 100 SKU)",
            "nota": (
                "Las zonas 2. PISO, 1. LLANTAS, 10. UBICACIÓN RECIBO, "
                "14. LATERALES y 6. RACK COLGANTES usan coordenadas "
                "placeholder (1 pasillo) hasta tener el desglose real "
                "de pasillos/ubicaciones del layout físico."
            ),
        },
        "skus": registros,
        "resumen_por_subzona": {
            f"{zona} / {subzona}": n
            for (zona, subzona), n in assigner.resumen().items()
        },
    }


if __name__ == "__main__":
    path_excel = sys.argv[1] if len(sys.argv) > 1 else "IMPULSA_CD_Analizado__2_.xlsx"
    path_salida = sys.argv[2] if len(sys.argv) > 2 else "digital_twin_data.json"

    dataset = construir_dataset(path_excel)

    with open(path_salida, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False, default=str)

    print(f"Exportado: {path_salida}")
    print(f"Total SKU: {dataset['meta']['total_skus']}")
    print(f"Rango heat: {dataset['meta']['heat_min']} - {dataset['meta']['heat_max']}")
