"""Fases 12 y 14 del notebook original -- recomendación final por SKU y
validación de factibilidad del resultado del optimizador.

Puerto de `MVP_Reslotting_Inchcape.ipynb` (celdas 98-104, 110-112), con
una simplificación real: el notebook re-extrae `ZONA_RECOMENDADA` leyendo
las variables binarias de PuLP porque es un script plano; aquí ya viene
como `ResultadoOptimizador.zona_asignada` (ver `optimizador.py`), así que
no hay que releer el modelo.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


class FactibilidadError(ValueError):
    """El resultado del optimizador no cumple una restricción dura --
    no debería ocurrir si `optimizador.py` está bien planteado, pero se
    valida explícitamente antes de exponer el resultado (Fase 14)."""


def construir_recomendaciones(
    base_con_score: pd.DataFrame,
    zona_asignada: dict[str, str],
    layout_cd: pd.DataFrame,
) -> pd.DataFrame:
    tiempos_zona = layout_cd.set_index("ZONA")["TIEMPO_MINUTOS"].to_dict()

    r = base_con_score.copy()
    r["ZONA_RECOMENDADA"] = r["SKU"].map(zona_asignada)
    r["TIEMPO_NUEVO_MIN"] = r["ZONA_RECOMENDADA"].map(tiempos_zona)
    r["COSTO_ACTUAL_MIN"] = r["N_LINEAS"] * r["TIEMPO_LAYOUT_ACTUAL"]
    r["COSTO_NUEVO_MIN"] = r["N_LINEAS"] * r["TIEMPO_NUEVO_MIN"]
    r["AHORRO_ESTIMADO_MIN"] = r["COSTO_ACTUAL_MIN"] - r["COSTO_NUEVO_MIN"]
    r["AHORRO_%"] = np.where(
        r["COSTO_ACTUAL_MIN"] > 0, 100 * r["AHORRO_ESTIMADO_MIN"] / r["COSTO_ACTUAL_MIN"], 0
    )
    r["MOVIMIENTO"] = np.where(r["ZONA_ACTUAL"] != r["ZONA_RECOMENDADA"], "MOVER", "MANTENER")
    r["JUSTIFICACION"] = r.apply(_generar_justificacion, axis=1)

    columnas = [
        "RANKING_SCORE",
        "SKU",
        "MARCA",
        "FAMILIA",
        "ABC",
        "ROTACION_6M",
        "N_PEDIDOS",
        "N_LINEAS",
        "CANT_TOTAL",
        "VOLUMEN_M3",
        "PESO_KG",
        "ZONA_ACTUAL",
        "ZONA_RECOMENDADA",
        "TIEMPO_LAYOUT_ACTUAL",
        "TIEMPO_NUEVO_MIN",
        "COSTO_ACTUAL_MIN",
        "COSTO_NUEVO_MIN",
        "AHORRO_ESTIMADO_MIN",
        "AHORRO_%",
        "SCORE_PRIORIDAD",
        "MOVIMIENTO",
        "JUSTIFICACION",
    ]
    columnas_ml = ["CLUSTER_ML", "PERFIL_ML", "PRIORIDAD_CLUSTER_RANK", "INDICE_IMPACTO_CLUSTER"]
    columnas += [c for c in columnas_ml if c in r.columns]  # solo si ml_perfil.py ya corrió antes

    return r[columnas].sort_values("AHORRO_ESTIMADO_MIN", ascending=False).reset_index(drop=True)


def _generar_justificacion(fila: pd.Series) -> str:
    if fila["MOVIMIENTO"] == "MOVER":
        return (
            f"Mover de {fila['ZONA_ACTUAL']} a {fila['ZONA_RECOMENDADA']}. "
            f"El SKU registró {int(fila['N_LINEAS'])} visitas. "
            f"El tiempo de acceso de zona pasa de {fila['TIEMPO_LAYOUT_ACTUAL']:.2f} a "
            f"{fila['TIEMPO_NUEVO_MIN']:.2f} min. "
            f"Ahorro estimado en la muestra: {fila['AHORRO_ESTIMADO_MIN']:.2f} min."
        )
    return (
        f"Mantener en {fila['ZONA_ACTUAL']}. Dentro de las restricciones actuales, "
        "el optimizador no seleccionó un cambio de zona."
    )


def validar_factibilidad(
    recomendaciones: pd.DataFrame, capacidad: pd.DataFrame, max_movimientos: int
) -> None:
    """Fase 14 -- repite, sobre el resultado ya extraído, las mismas tres
    comprobaciones duras que ya garantizan las restricciones del
    optimizador (cinturón y tirantes: si esto falla, hay un bug en
    `optimizador.py`, no un caso de negocio válido).
    """
    volumen_nuevo = (
        recomendaciones.groupby("ZONA_RECOMENDADA", as_index=False)["VOLUMEN_M3"]
        .sum()
        .rename(columns={"ZONA_RECOMENDADA": "ZONA", "VOLUMEN_M3": "VOLUMEN_SKU_ASIGNADOS"})
    )
    validacion = capacidad.merge(volumen_nuevo, on="ZONA", how="left")
    validacion["VOLUMEN_SKU_ASIGNADOS"] = validacion["VOLUMEN_SKU_ASIGNADOS"].fillna(0)
    validacion["VOLUMEN_FINAL_M3"] = (
        validacion["VOLUMEN_BASE_NO_MODELADO"] + validacion["VOLUMEN_SKU_ASIGNADOS"]
    )
    excedidas = validacion[validacion["VOLUMEN_FINAL_M3"] > validacion["CAPACIDAD_MAX_M3"] + 1e-9]
    if len(excedidas):
        raise FactibilidadError(f"Zonas que exceden capacidad: {excedidas['ZONA'].tolist()}")

    n_movidos = recomendaciones["MOVIMIENTO"].eq("MOVER").sum()
    if n_movidos > max_movimientos:
        raise FactibilidadError(f"Se superó el máximo de movimientos: {n_movidos} > {max_movimientos}")

    if recomendaciones["ZONA_RECOMENDADA"].isna().any():
        raise FactibilidadError("Hay SKU sin zona recomendada.")
