"""Fase 7 del notebook original -- Score Multicriterio.

Puerto directo de `MVP_Reslotting_Inchcape.ipynb` (celdas 54-60). El
score prioriza SKU; no decide por sí solo la zona final -- esa es
responsabilidad del optimizador (`dominio/optimizador.py`).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def normalizar_01(serie: pd.Series) -> pd.Series:
    """Min-max a [0, 1]. Si la serie es constante (min == max), devuelve
    todo ceros en vez de dividir por cero.
    """
    serie = serie.astype(float)
    minimo, maximo = serie.min(), serie.max()
    if pd.isna(minimo) or pd.isna(maximo) or maximo == minimo:
        return pd.Series(np.zeros(len(serie)), index=serie.index)
    return (serie - minimo) / (maximo - minimo)


def calcular_score_prioridad(
    base_maestra: pd.DataFrame,
    pesos: dict[str, float],
    mapa_abc: dict[str, float],
) -> pd.DataFrame:
    """Añade AHORRO_NORM, ROTACION_NORM, VOLUMEN_NORM,
    FACILIDAD_MOVIMIENTO, ABC_SCORE, SCORE_PRIORIDAD (0-100) y
    RANKING_SCORE a `base_maestra`.

    `pesos` debe sumar 1.0 -- se valida explícitamente, no se asume.
    """
    suma_pesos = sum(pesos.values())
    if abs(suma_pesos - 1) > 1e-4:
        raise ValueError(f"Los pesos del score deben sumar 1.0, suman {suma_pesos}")

    base_maestra = base_maestra.copy()
    base_maestra["AHORRO_NORM"] = normalizar_01(base_maestra["AHORRO_TEORICO_MIN"])
    base_maestra["ROTACION_NORM"] = normalizar_01(base_maestra["ROTACION_6M"])
    base_maestra["VOLUMEN_NORM"] = normalizar_01(base_maestra["VOLUMEN_M3"])
    base_maestra["FACILIDAD_MOVIMIENTO"] = 1 - base_maestra["VOLUMEN_NORM"]
    base_maestra["ABC_SCORE"] = base_maestra["ABC"].map(mapa_abc).fillna(0)

    base_maestra["SCORE_PRIORIDAD"] = 100 * (
        pesos["ahorro"] * base_maestra["AHORRO_NORM"]
        + pesos["rotacion"] * base_maestra["ROTACION_NORM"]
        + pesos["abc"] * base_maestra["ABC_SCORE"]
        + pesos["facilidad_movimiento"] * base_maestra["FACILIDAD_MOVIMIENTO"]
    )
    base_maestra["RANKING_SCORE"] = (
        base_maestra["SCORE_PRIORIDAD"].rank(method="dense", ascending=False).astype(int)
    )
    return base_maestra
