#!/usr/bin/env python3
"""Genera engine-data.json: la corrida del motor lista para el tablero.

Reproduce la lógica del notebook (carga operativa, score multicriterio y
asignación bajo el tope de traslados) sobre el export del gemelo digital, y
añade el plano de subzonas de zone_grid_config.py.

    python3 dashboard/export_dashboard_data.py
    python3 dashboard/build.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TWIN = ROOT / "gemelo_digital" / "digital_twin_data.json"
CONFIG = ROOT / "gemelo_digital" / "zone_grid_config.py"
OUT = Path(__file__).parent / "engine-data.json"

MAX_MOV = 20                      # tope del optimizador: 20 % del catálogo
PESOS = {"ahorro": 0.55, "rot": 0.20, "abc": 0.10, "fac": 0.15}
ABC_SCORE = {"A": 1.0, "B": 0.6, "C": 0.3}
TARIFA_USD_H = 6.0


def leer_plano() -> list[dict]:
    """Extrae las SubZona(...) declaradas en zone_grid_config.py."""
    txt = CONFIG.read_text(encoding="utf-8")
    bloques = re.findall(r'"([^"]+)":\s*\[(.*?)\]', txt, re.S)
    plano = []
    for zona, cuerpo in bloques:
        for m in re.finditer(
            r'SubZona\(\s*"([^"]+)",\s*n_pasillos=(\d+),\s*n_ubicaciones=(\d+),'
            r'\s*operacion="([^"]+)"(?:,\s*n_niveles=(\d+))?', cuerpo):
            nombre, pas, ubic, oper, niv = m.groups()
            niveles = int(niv) if niv else (6 if oper in ("Reach", "Grua") else 4)
            plano.append(dict(zona=zona, sub=nombre, pasillos=int(pas),
                              ubicaciones=int(ubic), niveles=niveles,
                              op=oper, placeholder=int(ubic) == 1))
    return plano


def main() -> None:
    twin = json.loads(TWIN.read_text(encoding="utf-8"))
    sk = twin["skus"]

    ZT = {s["zona_excel"]: s["tiempo_acceso_min"] for s in sk}
    ZD = {s["zona_excel"]: s["distancia_m"] for s in sk}
    tmin = min(ZT.values())
    zmin = min(ZT, key=ZT.get)

    rows = []
    for s in sk:
        costo = s["rotacion_6m"] * ZT[s["zona_excel"]]
        ahorro = max(0.0, s["rotacion_6m"] * (ZT[s["zona_excel"]] - tmin))
        rows.append(dict(
            sku=s["sku"], marca=s["marca"], fam=s["familia"], abc=s["abc"],
            rot=s["rotacion_6m"], zona=s["zona_excel"], sub=s["subzona"],
            t=ZT[s["zona_excel"]], d=ZD[s["zona_excel"]],
            vol=round(s["volumen_m3"], 3), peso=round(s["peso_kg"], 2),
            px=s["pasillo_x"], py=s["posicion_y"], pz=s["nivel_z"],
            op=s["operacion"], grua=s["requiere_grua"], heat=s["heat_tiempo_picking"],
            costo=round(costo, 1), ahorro=round(ahorro, 1)))

    # el optimizador gasta su presupuesto en los traslados de mayor ahorro
    rows.sort(key=lambda r: -r["ahorro"])
    for i, r in enumerate(rows):
        r["mover"] = i < MAX_MOV
        r["dest"] = zmin if i < MAX_MOV else r["zona"]

    def norm(vals):
        lo, hi = min(vals), max(vals)
        return lambda v: 0.0 if hi == lo else (v - lo) / (hi - lo)

    n_ah = norm([r["ahorro"] for r in rows])
    n_ro = norm([r["rot"] for r in rows])
    n_vo = norm([r["vol"] for r in rows])
    for r in rows:
        nah, nro, fac = n_ah(r["ahorro"]), n_ro(r["rot"]), 1 - n_vo(r["vol"])
        r["n"] = {"ahorro": round(nah, 4), "rot": round(nro, 4),
                  "abc": ABC_SCORE[r["abc"]], "fac": round(fac, 4)}
        r["score"] = round(100 * (PESOS["ahorro"] * nah + PESOS["rot"] * nro
                                  + PESOS["abc"] * ABC_SCORE[r["abc"]]
                                  + PESOS["fac"] * fac), 1)
    for i, r in enumerate(sorted(rows, key=lambda r: -r["score"])):
        r["rank"] = i + 1

    zonas = sorted((dict(
        z=k, t=ZT[k], d=ZD[k],
        n=sum(1 for r in rows if r["zona"] == k),
        carga=round(sum(r["costo"] for r in rows if r["zona"] == k), 1),
        pot=round(sum(r["ahorro"] for r in rows if r["zona"] == k), 1),
        mov=sum(1 for r in rows if r["mover"] and r["zona"] == k),
    ) for k in ZT), key=lambda z: -z["carga"])

    plano = leer_plano()
    ocupados = {}
    for r in rows:
        ocupados[(r["zona"], r["sub"])] = ocupados.get((r["zona"], r["sub"]), 0) + 1
    for p in plano:
        p["skus"] = ocupados.get((p["zona"], p["sub"]), 0)
        p["posiciones"] = p["ubicaciones"] * (1 if p["placeholder"] else 1)

    out = {
        "meta": {
            "tmin": tmin, "zmin": zmin, "tarifa_usd_h": TARIFA_USD_H,
            "skus": len(rows), "zonas": len(ZT), "escenarios": len(rows) * len(ZT),
            "max_mov": MAX_MOV, "pesos": PESOS,
            "cobertura": twin["meta"]["cobertura_almacen"], "nota": twin["meta"]["nota"],
            "heat_min": twin["meta"]["heat_min"], "heat_max": twin["meta"]["heat_max"],
        },
        "zonas": zonas, "skus": rows, "plano": plano,
        "subzonas": twin["resumen_por_subzona"],
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tot = sum(r["costo"] for r in rows)
    ah = sum(r["ahorro"] for r in rows if r["mover"])
    print(f"engine-data.json · {len(rows)} SKU · {len(zonas)} zonas · {len(plano)} subzonas")
    print(f"carga {tot/60:,.1f} h-h · ahorro {ah/60:,.1f} h-h ({100*ah/tot:.2f} %) · USD {ah/60*TARIFA_USD_H:,.0f}")


if __name__ == "__main__":
    main()
