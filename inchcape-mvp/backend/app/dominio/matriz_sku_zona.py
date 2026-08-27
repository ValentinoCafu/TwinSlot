"""Fase 8 del notebook original -- Evaluación SKU × Zona.

Puerto directo de `MVP_Reslotting_Inchcape.ipynb` (celdas 62-72). Con
N SKU y M zonas se generan N×M escenarios -- nunca "900" hardcodeado,
siempre `len(base_maestra) * len(layout_cd)` (principio §4.3 de
`propuesta-mvp-dos-niveles-sintetico-vs-real.md`).
"""

from __future__ import annotations

import pandas as pd


class MatrizSkuZonaInvalidaError(ValueError):
    """La matriz SKU × Zona no tiene la forma esperada (N×M escenarios,
    exactamente una fila marcada como zona actual por SKU)."""


def construir_matriz_sku_zona(base_maestra: pd.DataFrame, layout_cd: pd.DataFrame) -> pd.DataFrame:
    """Producto cartesiano SKU × Zona con el costo operativo de cada
    escenario.

    Costo nuevo = N_LINEAS × tiempo de la zona candidata.
    Ahorro = Carga operativa actual − costo nuevo.
    """
    sku_para_evaluar = base_maestra.copy()
    zonas_para_evaluar = layout_cd[["ZONA", "DISTANCIA_METROS", "TIEMPO_MINUTOS", "CAPACIDAD_M3_MAX"]].copy()

    sku_para_evaluar["KEY"] = 1
    zonas_para_evaluar["KEY"] = 1
    matriz = sku_para_evaluar.merge(zonas_para_evaluar, on="KEY").drop(columns="KEY")

    matriz["COSTO_NUEVO_MIN"] = matriz["N_LINEAS"] * matriz["TIEMPO_MINUTOS"]
    matriz["AHORRO_MIN"] = matriz["CARGA_OPERATIVA_MIN"] - matriz["COSTO_NUEVO_MIN"]
    matriz["ES_ZONA_ACTUAL"] = matriz["ZONA"] == matriz["ZONA_ACTUAL"]

    _validar_matriz(matriz, base_maestra, layout_cd)
    return matriz


def _validar_matriz(matriz: pd.DataFrame, base_maestra: pd.DataFrame, layout_cd: pd.DataFrame) -> None:
    n_esperado = len(base_maestra) * len(layout_cd)
    if len(matriz) != n_esperado:
        raise MatrizSkuZonaInvalidaError(
            f"Se esperaban {n_esperado} escenarios ({len(base_maestra)} SKU × "
            f"{len(layout_cd)} zonas), se obtuvieron {len(matriz)}."
        )
    escenarios_por_sku = matriz.groupby("SKU").size()
    if escenarios_por_sku.min() != len(layout_cd) or escenarios_por_sku.max() != len(layout_cd):
        raise MatrizSkuZonaInvalidaError("No todos los SKU tienen exactamente una fila por zona.")

    zonas_actuales_en_matriz = matriz.groupby("SKU")["ES_ZONA_ACTUAL"].sum()
    if zonas_actuales_en_matriz.min() != 1 or zonas_actuales_en_matriz.max() != 1:
        raise MatrizSkuZonaInvalidaError(
            "Cada SKU debe tener exactamente una fila marcada como su zona actual "
            "(zona_actual debe existir en layout_cd)."
        )


def mejor_zona_teorica(matriz: pd.DataFrame) -> pd.DataFrame:
    """Fase 8.5 -- la zona que minimiza el costo operativo por SKU, sin
    considerar todavía capacidad ni el tope de movimientos (eso lo
    aplica el optimizador).
    """
    mejor = (
        matriz.sort_values(["SKU", "COSTO_NUEVO_MIN"])
        .groupby("SKU", as_index=False)
        .first()[
            [
                "SKU",
                "ZONA_ACTUAL",
                "ZONA",
                "N_LINEAS",
                "TIEMPO_LAYOUT_ACTUAL",
                "TIEMPO_MINUTOS",
                "CARGA_OPERATIVA_MIN",
                "COSTO_NUEVO_MIN",
                "AHORRO_MIN",
                "SCORE_PRIORIDAD",
                "RANKING_SCORE",
            ]
        ]
        .rename(
            columns={
                "ZONA": "MEJOR_ZONA_TEORICA",
                "TIEMPO_MINUTOS": "MEJOR_TIEMPO_TEORICO",
                "AHORRO_MIN": "MEJOR_AHORRO_TEORICO",
            }
        )
    )
    return mejor
