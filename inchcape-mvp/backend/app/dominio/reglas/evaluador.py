"""Motor de reglas propio (no `business-rules`, por el riesgo de
mantenimiento ya señalado en `propuesta-motor-reglas-y-explicabilidad.md`
§4). Nunca usa `eval` -- los operadores son un mapa fijo y seguro.

Ninguna regla de seguridad puede ser "superada" por un buen score: estas
funciones producen restricciones DURAS que se pasan al optimizador como
variables fijadas a 0/1, nunca como un término más del score.
"""

from __future__ import annotations

import operator as _op
from dataclasses import dataclass, field

import pandas as pd

from app.dominio.reglas.modelos import Regla

OPERADORES = {"==": _op.eq, "!=": _op.ne, ">": _op.gt, ">=": _op.ge, "<": _op.lt, "<=": _op.le}


def _cumple(valor_sku, operador: str, valor_regla) -> bool:
    if valor_sku is None or (isinstance(valor_sku, float) and pd.isna(valor_sku)):
        return False
    return OPERADORES[operador](valor_sku, valor_regla)


@dataclass
class ResultadoReglasAtributo:
    zona_unica_por_sku: dict[str, str] = field(default_factory=dict)
    zonas_excluidas_por_sku: dict[str, set[str]] = field(default_factory=dict)
    camino_decision: list[dict] = field(default_factory=list)  # [{sku, regla_id, motivo}]


def aplicar_reglas_atributo(base_maestra: pd.DataFrame, reglas: list[Regla]) -> ResultadoReglasAtributo:
    resultado = ResultadoReglasAtributo()
    reglas_activas = [r for r in reglas if r.activa and r.tipo == "atributo"]
    if not reglas_activas:
        return resultado

    for _, fila in base_maestra.iterrows():
        for regla in reglas_activas:
            d = regla.definicion
            if d.campo not in fila:
                continue
            if not _cumple(fila[d.campo], d.operador, d.valor):
                continue

            sku = fila["SKU"]
            if d.zona_permitida:
                resultado.zona_unica_por_sku[sku] = d.zona_permitida
                resultado.camino_decision.append(
                    {
                        "sku": sku,
                        "regla_id": regla.id,
                        "motivo": f"{regla.nombre}: forzado a zona '{d.zona_permitida}'",
                    }
                )
            if d.zona_prohibida:
                resultado.zonas_excluidas_por_sku.setdefault(sku, set()).add(d.zona_prohibida)
                resultado.camino_decision.append(
                    {
                        "sku": sku,
                        "regla_id": regla.id,
                        "motivo": f"{regla.nombre}: excluida zona '{d.zona_prohibida}'",
                    }
                )
    return resultado


def pares_familias_incompatibles(reglas: list[Regla]) -> list[tuple[str, str]]:
    """Solo modo 'misma_zona_prohibida' (Nivel 1) -- distancia mínima en
    metros queda pendiente de la geometría absoluta confirmada."""
    return [
        (r.definicion.familia_a, r.definicion.familia_b)
        for r in reglas
        if r.activa and r.tipo == "incompatibilidad" and r.definicion.modo == "misma_zona_prohibida"
    ]


def evaluar_umbral(valor: float, regla: Regla) -> bool:
    """True si el valor CUMPLE el umbral (ej. payback <= 3 meses)."""
    d = regla.definicion
    return _cumple(valor, d.operador, d.valor_umbral)
