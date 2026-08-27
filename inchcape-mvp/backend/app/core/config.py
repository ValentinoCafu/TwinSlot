"""Configuración central del backend.

Ninguna ruta ni constante de negocio se hardcodea en los módulos de
dominio o en los routers -- todo pasa por aquí, siguiendo el principio
de "nunca hardcodear la escala del catálogo" de
`propuesta-mvp-dos-niveles-sintetico-vs-real.md` §4.3.
"""

import os
from pathlib import Path

# Raíz de MVP-Inchape/backend/
BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "data"
# Override vía MVP_DB_PATH para pruebas -- nunca apuntar los tests a mvp.db real.
DB_PATH = Path(os.environ.get("MVP_DB_PATH", BASE_DIR / "mvp.db"))
CONFIG_MAPEO_DEFAULT_PATH = DATA_DIR / "config_mapeo.yaml"
ZONAS_JSON_PATH = DATA_DIR / "zonas.json"

# CORS -- orígenes permitidos del frontend Vite en desarrollo local
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# Parámetros de negocio (no de infraestructura) -- ajustables sin tocar
# lógica de dominio; el optimizador y el ranking los leen de aquí.
PORCENTAJE_TOP_INICIAL = 0.20  # Fase 5.5 del notebook: 20% de SKU con mayor ahorro teórico
PORCENTAJE_MAX_MOVIMIENTO = 0.20  # Fase 10.7 del notebook: tope de SKU movidos por el optimizador
PENALIZACION_MOVIMIENTO = 0.0  # min. adicionales por mover un SKU -- 0 hasta que exista costo real validado
ZONAS_NO_DESTINO: list[str] = (
    []
)  # zonas bloqueadas como destino nuevo (Fase 10.8) -- editable por Operaciones

# Fase 7.3 del notebook -- pesos del score ponderado. "Deben validarse
# posteriormente con Operaciones" (nota original del notebook, se mantiene).
PESOS_SCORE = {
    "ahorro": 0.55,
    "rotacion": 0.20,
    "abc": 0.10,
    "facilidad_movimiento": 0.15,
}
MAPA_ABC_SCORE = {"A": 1.00, "B": 0.60, "C": 0.30}
