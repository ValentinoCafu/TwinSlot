"""Extrae de un SVG exportado por Synoptic Designer (fondo trazado +
capa vectorial de zonas) la geometria real de cada zona ya dibujada: el
poligono de borde (el <path> con `title`) y los <rect> individuales de
espacio dentro de su grupo, resolviendo las transformaciones SVG
(translate/matrix/rotate/scale) a coordenadas finales absolutas.

Uso (desde la raiz de MVP-Inchape):
    conda run -n IngenieriaPython python scripts/extraer_layout_svg.py \
        "layout  inchape v3.svg" frontend/src/data/layoutV3.json

Ver `LAYOUT-SVG-V3.md` para el contrato completo: como debe estar
armado el SVG en el editor para que este script lo reconozca, y como
se integra el resultado en el frontend.
"""

from __future__ import annotations

import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

Matriz = tuple[float, float, float, float, float, float]
IDENTIDAD: Matriz = (1, 0, 0, 1, 0, 0)


def _local(tag: str) -> str:
    return tag.split("}")[-1]


def _mat_mul(m1: Matriz, m2: Matriz) -> Matriz:
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    )


def parse_transform(t: str | None) -> Matriz:
    """Combina translate/matrix/scale/rotate de un atributo `transform`,
    en el orden en que aparecen (izquierda a derecha == de afuera hacia
    adentro, como especifica SVG)."""
    if not t:
        return IDENTIDAD
    m = IDENTIDAD
    for nombre, args in re.findall(r"(\w+)\(([^)]+)\)", t):
        nums = [float(x) for x in re.split(r"[ ,]+", args.strip()) if x]
        if nombre == "translate":
            local_m: Matriz = (1, 0, 0, 1, nums[0], nums[1] if len(nums) > 1 else 0)
        elif nombre == "matrix":
            local_m = tuple(nums)  # type: ignore[assignment]
        elif nombre == "scale":
            sx = nums[0]
            sy = nums[1] if len(nums) > 1 else sx
            local_m = (sx, 0, 0, sy, 0, 0)
        elif nombre == "rotate":
            ang = math.radians(nums[0])
            cx, cy = (nums[1], nums[2]) if len(nums) > 2 else (0.0, 0.0)
            cos_a, sin_a = math.cos(ang), math.sin(ang)
            rot: Matriz = (cos_a, sin_a, -sin_a, cos_a, 0, 0)
            local_m = _mat_mul(_mat_mul((1, 0, 0, 1, cx, cy), rot), (1, 0, 0, 1, -cx, -cy))
        else:
            local_m = IDENTIDAD
        m = _mat_mul(m, local_m)
    return m


def _apply(m: Matriz, x: float, y: float) -> tuple[float, float]:
    a, b, c, d, e, f = m
    return (a * x + c * y + e, b * x + d * y + f)


def extraer(ruta_svg: Path) -> dict:
    tree = ET.parse(ruta_svg)
    root = tree.getroot()
    view_box = root.get("viewBox")

    grupos = [el for el in root.iter() if _local(el.tag) == "g" and (el.get("id") or "").startswith("Grupo_x20_")]

    resultado: dict = {"view_box": view_box, "zonas": {}}
    for g in grupos:
        gid = g.get("id", "")
        nombre = gid.replace("Grupo_x20_", "").replace("_x20_", " ")
        hijos = list(g.iter())
        paths = [e for e in hijos if _local(e.tag) == "path"]
        rects = [e for e in hijos if _local(e.tag) == "rect"]
        boundary = next((p for p in paths if p.get("title")), None)

        espacios = []
        no_axial = 0
        for r in rects:
            m = parse_transform(r.get("transform"))
            if abs(m[1]) > 1e-6 or abs(m[2]) > 1e-6:
                no_axial += 1
            x, y = float(r.get("x", 0)), float(r.get("y", 0))
            w, h = float(r.get("width", 0)), float(r.get("height", 0))
            x0, y0 = _apply(m, x, y)
            x1, y1 = _apply(m, x + w, y + h)
            espacios.append(
                {
                    "id": r.get("id"),
                    "x": round(min(x0, x1), 2),
                    "y": round(min(y0, y1), 2),
                    "ancho": round(abs(x1 - x0), 2),
                    "alto": round(abs(y1 - y0), 2),
                }
            )

        if no_axial:
            print(
                f"AVISO: {nombre} tiene {no_axial} rects con rotacion/escesgo no-axial -- "
                "sus x/y/ancho/alto son solo el bounding box, no la forma real.",
                file=sys.stderr,
            )

        resultado["zonas"][nombre] = {
            "titulo": boundary.get("title") if boundary is not None else None,
            "boundary_d": boundary.get("d") if boundary is not None else None,
            "espacios": espacios,
        }
    return resultado


def main() -> None:
    if len(sys.argv) != 3:
        print("Uso: python extraer_layout_svg.py <entrada.svg> <salida.json>", file=sys.stderr)
        raise SystemExit(1)
    entrada, salida = Path(sys.argv[1]), Path(sys.argv[2])
    datos = extraer(entrada)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    for nombre, z in datos["zonas"].items():
        print(f"{nombre}: {len(z['espacios'])} espacios")
    print(f"\nGuardado en {salida}")


if __name__ == "__main__":
    main()
