"""Genera una copia liviana de un SVG de Synoptic Designer, quitando
SOLO la imagen de fondo trazada (embebida en base64 -- es la parte que
pesa casi todo el archivo y no se usa para nada en el frontend, ver
`LAYOUT-SVG-V3.md` #1). No toca ninguna zona, path ni rect real -- si
necesitas seguir trazando con la imagen de referencia, sigue editando
el original, no esta copia.

Uso:
    conda run -n IngenieriaPython python scripts/limpiar_layout_svg.py \
        "layout  inchape v3.svg" "layout-inchape-v3-limpio.svg"
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)


def _local(tag: str) -> str:
    return tag.split("}")[-1]


def limpiar(entrada: Path, salida: Path) -> None:
    tree = ET.parse(entrada)
    root = tree.getroot()

    eliminados = []
    for padre in list(root.iter()):
        for hijo in list(padre):
            if hijo.get("data-synoptic-designer-tracing-layer") == "true":
                padre.remove(hijo)
                eliminados.append(hijo.get("id") or _local(hijo.tag))

    tree.write(salida, encoding="unicode", xml_declaration=False)

    tam_entrada = entrada.stat().st_size
    tam_salida = salida.stat().st_size
    print(f"Grupos eliminados (capa de imagen de fondo trazada): {eliminados}")
    print(f"Tamaño original: {tam_entrada / 1024:.0f} KB -> limpio: {tam_salida / 1024:.0f} KB")


def main() -> None:
    if len(sys.argv) != 3:
        print("Uso: python limpiar_layout_svg.py <entrada.svg> <salida.svg>", file=sys.stderr)
        raise SystemExit(1)
    limpiar(Path(sys.argv[1]), Path(sys.argv[2]))


if __name__ == "__main__":
    main()
