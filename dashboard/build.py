#!/usr/bin/env python3
"""Inyecta engine-data.json dentro de index.src.html y escribe index.html.

El dashboard queda como un único archivo autocontenido: se abre con doble clic,
sin servidor. Volver a correr este script tras regenerar engine-data.json.
"""
from pathlib import Path

base = Path(__file__).parent
src = (base / "index.src.html").read_text(encoding="utf-8")
data = (base / "engine-data.json").read_text(encoding="utf-8")

assert "/*__DATA__*/" in src, "falta el marcador /*__DATA__*/ en index.src.html"
out = src.replace("/*__DATA__*/", data)

(base / "index.html").write_text(out, encoding="utf-8")
print(f"index.html · {len(out) / 1024:.1f} KB")
