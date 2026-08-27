"""Fase 9 del notebook original -- Capacidad y ocupación.

Puerto directo de `MVP_Reslotting_Inchcape.ipynb` (celdas 74-78).

Hallazgo ya validado en CLAUDE_1.md punto 4 (26.16 m³ de SKU vs. 2 680 m³
de capacidad total, 0.98% de uso): la restricción de capacidad es vacua
en el dataset de práctica. Esta función lo sigue calculando igual --
el diagnóstico correcto es que el propio dato lo revele, no ocultarlo.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def calcular_capacidad(base_maestra: pd.DataFrame, ocupacion_zona: pd.DataFrame) -> pd.DataFrame:
    """Volumen base no modelado = volumen usado reportado − volumen de
    los SKU de la muestra ya presentes en esa zona (evita contar dos
    veces el mismo volumen si la ocupación reportada ya lo incluye).
    """
    volumen_actual_muestra = (
        base_maestra.groupby("ZONA_ACTUAL", as_index=False)["VOLUMEN_M3"]
        .sum()
        .rename(columns={"ZONA_ACTUAL": "ZONA", "VOLUMEN_M3": "VOLUMEN_MUESTRA_ACTUAL"})
    )

    capacidad = ocupacion_zona.merge(volumen_actual_muestra, on="ZONA", how="left")
    capacidad["VOLUMEN_MUESTRA_ACTUAL"] = capacidad["VOLUMEN_MUESTRA_ACTUAL"].fillna(0)
    capacidad["VOLUMEN_BASE_NO_MODELADO"] = (
        capacidad["VOLUMEN_USADO_M3"] - capacidad["VOLUMEN_MUESTRA_ACTUAL"]
    ).clip(lower=0)

    capacidad["USO_MODELO_ACTUAL_%"] = np.where(
        capacidad["CAPACIDAD_MAX_M3"] > 0,
        100 * capacidad["VOLUMEN_USADO_M3"] / capacidad["CAPACIDAD_MAX_M3"],
        0,
    )
    return capacidad
