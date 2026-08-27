"""Capa de mapeo configurable.

Los nombres de columna del Excel de práctica (`SKU`, `ROTACION_6M`, ...)
son los que existen HOY. Cuando la fuente sea un export real de SAP MM o
del WMS Brainsys, los nombres de columna casi con certeza serán distintos
-- ese es el riesgo explícito que señala
`Informacion de Otro Chat/sintesis-arquitectura-mvp-presentacion.md` §1.

Este módulo traduce nombre-de-origen -> nombre-canónico usando un YAML
editable, sin tocar código. Si no se sube un YAML, se usa
`DEFAULT_MAPEO`, que es la identidad sobre el Excel de práctica.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from app.core.config import CONFIG_MAPEO_DEFAULT_PATH

# tabla_canonica -> {"hoja": nombre de hoja/archivo esperado,
#                     "columnas": {canonico: origen}}
DEFAULT_MAPEO: dict[str, dict] = {
    "sku_maestro": {
        "hoja": "MAESTRO_SKUs",
        "columnas": {
            "SKU": "SKU",
            "MARCA": "MARCA",
            "FAMILIA": "FAMILIA",
            "VOLUMEN_M3": "VOLUMEN_M3",
            "PESO_KG": "PESO_KG",
        },
    },
    "rotacion": {
        "hoja": "ROTACIÓN",
        "columnas": {"SKU": "SKU", "ROTACION_6M": "ROTACION_6M", "ABC": "ABC"},
    },
    "stock_actual": {
        "hoja": "STOCK_ACTUAL",
        "columnas": {"UBICACION": "UBICACIÓN", "SKU": "SKU", "ZONA_ACTUAL": "ZONA_ACTUAL"},
    },
    "layout_cd": {
        "hoja": "LAYOUT_CD",
        "columnas": {
            "ZONA": "ZONA",
            "DISTANCIA_METROS": "DISTANCIA_METROS",
            "TIEMPO_MINUTOS": "TIEMPO_MINUTOS",
            "CAPACIDAD_M3_MAX": "CAPACIDAD_M3_MAX",
        },
    },
    "ocupacion_zona": {
        "hoja": "OCUPACION_POR_ZONA",
        "columnas": {
            "ZONA": "ZONA",
            "CAPACIDAD_MAX_M3": "CAPACIDAD_MAX_M3",
            "VOLUMEN_USADO_M3": "VOLUMEN_USADO_M3",
            "VOLUMEN_DISPONIBLE_M3": "VOLUMEN_DISPONIBLE_M3",
            "PORCENTAJE_USO": "PORCENTAJE_USO_%",
        },
    },
    "pedidos": {
        "hoja": "PEDIDOS ACTUAL",
        "columnas": {
            "PEDIDO_ID": "PEDIDO_ID",
            "LINEA": "LINEA",
            "SKU": "SKU",
            "CANTIDAD": "CANTIDAD",
            "ZONA_ACTUAL": "ZONA_ACTUAL",
            "TIEMPO_HOY_MIN": "TIEMPO_HOY_MIN",
        },
    },
}


def cargar_config_mapeo(path: str | Path | None = None) -> dict:
    """Carga el YAML de mapeo. Si no se provee, usa el default (identidad)."""
    ruta = Path(path) if path else CONFIG_MAPEO_DEFAULT_PATH
    if not ruta.exists():
        return DEFAULT_MAPEO
    with open(ruta, encoding="utf-8") as f:
        contenido = yaml.safe_load(f)
    return contenido if contenido else DEFAULT_MAPEO


def hoja_esperada(tabla: str, mapeo: dict) -> str:
    return mapeo[tabla]["hoja"]


def aplicar_mapeo(df: pd.DataFrame, tabla: str, mapeo: dict) -> pd.DataFrame:
    """Renombra columnas de origen a nombres canónicos y selecciona solo
    las columnas requeridas, en el orden canónico.

    Lanza ValueError (falla dura de ingesta, no rechazo fila a fila) si
    falta una columna de origen completa -- eso no es un dato sucio, es
    un archivo que no corresponde a la tabla esperada.
    """
    columnas = mapeo[tabla]["columnas"]
    faltantes = [origen for origen in columnas.values() if origen not in df.columns]
    if faltantes:
        raise ValueError(
            f"La hoja/archivo para '{tabla}' no tiene las columnas de origen "
            f"esperadas: {faltantes}. Columnas disponibles: {df.columns.tolist()}"
        )
    renombre = {origen: canonico for canonico, origen in columnas.items()}
    return df.rename(columns=renombre)[list(columnas.keys())].copy()
