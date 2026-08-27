"""Una bandera de activación por módulo -- el mismo patrón ya validado
con el motor de afinidad (`if modularidad_observada <= percentil_95_nulo:
usar_afinidad = False`): cada módulo detecta en tiempo de ejecución si
tiene datos suficientes, nunca simula con datos inventados
(`propuesta-mvp-dos-niveles-sintetico-vs-real.md` §0).

Pasar de Nivel 1 a Nivel 2 es alimentar estas tablas, no reescribir
código -- por eso las banderas leen la base de datos directamente, no un
parámetro que alguien tendría que acordarse de pasar.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from app.core.db import engine


def _tabla_tiene_filas(nombre_tabla: str) -> bool:
    with engine.connect() as conn:
        fila = conn.execute(text(f"SELECT 1 FROM {nombre_tabla} LIMIT 1")).first()
    return fila is not None


def _stock_tiene_columna(nombre_columna: str) -> bool:
    with engine.connect() as conn:
        columnas = pd.read_sql("SELECT * FROM stock_actual LIMIT 0", conn).columns
    return nombre_columna in columnas


def evaluar_banderas() -> dict[str, bool]:
    return {
        # Requiere la cota real del plano + punto I/O confirmado --
        # pendiente más citado del proyecto (CLAUDE_1.md #10-11).
        "usar_incompatibilidad_geometrica": False,
        # Requiere SLOTTING_INICIAL: SKU, zona, fecha, tiempo teórico.
        "usar_triage": _tabla_tiene_filas("slotting_inicial"),
        # Requiere histórico mensual (6+ filas por SKU) para comparar
        # baseline vs. actual.
        "usar_payback_real": _tabla_tiene_filas("historico_mensual"),
        # Requiere fecha de lote/vencimiento en stock_actual -- no
        # existe en el dataset de práctica.
        "usar_fifo": _stock_tiene_columna("FECHA_LOTE"),
    }
