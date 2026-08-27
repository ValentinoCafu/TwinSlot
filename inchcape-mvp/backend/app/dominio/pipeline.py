"""Orquesta las Fases 3-14 en una sola llamada: éste es el cuerpo de
`POST /pipeline/ejecutar`. Cada paso es una función pura de otro módulo
de `dominio/` -- este archivo solo encadena datos, no calcula nada.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.core.config import (
    MAPA_ABC_SCORE,
    PENALIZACION_MOVIMIENTO,
    PESOS_SCORE,
    PORCENTAJE_MAX_MOVIMIENTO,
    ZONAS_NO_DESTINO,
)
from app.dominio.capacidad import calcular_capacidad
from app.dominio.impacto import calcular_impacto_operativo, construir_base_maestra
from app.dominio.indicadores import construir_pedidos_por_sku
from app.dominio.kpis import calcular_kpis
from app.dominio.ml_perfil import ResultadoML, calcular_ml_perfil
from app.dominio.optimizador import ejecutar_optimizador
from app.dominio.recomendaciones import construir_recomendaciones, validar_factibilidad
from app.dominio.reglas.evaluador import aplicar_reglas_atributo, pares_familias_incompatibles
from app.dominio.reglas.modelos import Regla
from app.dominio.scoring import calcular_score_prioridad


class SinLoteIngeridoError(ValueError):
    """No hay datos cargados -- llamar POST /ingesta antes del pipeline."""


@dataclass
class ResultadoPipeline:
    recomendaciones: pd.DataFrame
    kpis: dict
    camino_decision_reglas: list[dict]
    ml: ResultadoML


def ejecutar_pipeline(
    datasets: dict[str, pd.DataFrame],
    pesos_score: dict[str, float] | None = None,
    porcentaje_max_movimiento: float | None = None,
    reglas: list[Regla] | None = None,
) -> ResultadoPipeline:
    if datasets["sku_maestro"].empty or datasets["pedidos"].empty:
        raise SinLoteIngeridoError("No hay un lote ingerido. Llama POST /ingesta primero.")

    pesos_score = pesos_score or PESOS_SCORE
    porcentaje_max_movimiento = (
        PORCENTAJE_MAX_MOVIMIENTO if porcentaje_max_movimiento is None else porcentaje_max_movimiento
    )

    pedidos_por_sku = construir_pedidos_por_sku(datasets["pedidos"])
    base = construir_base_maestra(
        datasets["sku_maestro"],
        datasets["rotacion"],
        datasets["stock_actual"],
        pedidos_por_sku,
        datasets["layout_cd"],
    )
    impacto = calcular_impacto_operativo(base, datasets["layout_cd"])
    base_con_score = calcular_score_prioridad(impacto.base_maestra, pesos_score, MAPA_ABC_SCORE)

    resultado_ml = calcular_ml_perfil(base_con_score)
    base_con_score = resultado_ml.base_con_ml  # + CLUSTER_ML, PERFIL_ML, DISTANCIA_CENTROIDE, ...

    capacidad = calcular_capacidad(base_con_score, datasets["ocupacion_zona"])

    reglas = reglas or []
    reglas_atributo = aplicar_reglas_atributo(base_con_score, reglas)
    pares_incompatibles = pares_familias_incompatibles(reglas)

    resultado_opt = ejecutar_optimizador(
        base_con_score,
        datasets["layout_cd"],
        capacidad,
        porcentaje_max_movimiento,
        zonas_no_destino=ZONAS_NO_DESTINO,
        penalizacion_movimiento=PENALIZACION_MOVIMIENTO,
        zona_unica_por_sku=reglas_atributo.zona_unica_por_sku,
        zonas_excluidas_por_sku=reglas_atributo.zonas_excluidas_por_sku,
        pares_familias_incompatibles=pares_incompatibles,
    )
    recomendaciones = construir_recomendaciones(
        base_con_score, resultado_opt.zona_asignada, datasets["layout_cd"]
    )
    validar_factibilidad(recomendaciones, capacidad, resultado_opt.max_movimientos)
    n_pedidos = datasets["pedidos"]["PEDIDO_ID"].nunique()
    kpis = calcular_kpis(recomendaciones, resultado_opt.max_movimientos, n_pedidos)

    return ResultadoPipeline(
        recomendaciones=recomendaciones,
        kpis=kpis,
        camino_decision_reglas=reglas_atributo.camino_decision,
        ml=resultado_ml,
    )
