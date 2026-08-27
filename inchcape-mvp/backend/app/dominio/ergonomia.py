"""Banda de oro ergonómica NIOSH -- antropometría peruana.

Los valores de RWL de los dos escenarios (favorable/conservador) ya
fueron calculados y validados en una entrega previa del proyecto (ver
`CLAUDE_1.md` puntos 12-14: ecuación NIOSH revisada
RWL = 23·HM·VM·DM·AM·FM·CM, aplicada con los parámetros posturales del
CD). Se citan aquí como supuesto declarado -- re-derivar los seis
multiplicadores (HM, VM, DM, AM, FM, CM) desde cero no es una variable
libre de este MVP, ya se fijó y quedó documentada.

Depende solo de PESO_KG, un atributo estático del SKU -- por eso está
✅ completo en Nivel 1, no requiere historia (tabla maestra del
`propuesta-mvp-dos-niveles-sintetico-vs-real.md`).
"""

from __future__ import annotations

import pandas as pd

BANDA_ORO_CM_MIN = 82.5  # P95 altura-nudillo varón
BANDA_ORO_CM_MAX = 113.4  # P5 altura-hombro mujer
CONSTANTE_NIOSH_KG = 23.0  # límite genérico de la ecuación NIOSH, sin ajustar por postura
RWL_FAVORABLE_KG = 21.3  # H=25cm, D=25cm, A=0°, FM=1.0, acople bueno
RWL_CONSERVADOR_KG = 11.4  # H=35cm, FM=0.75, acople regular


def calcular_ergonomia(base_maestra: pd.DataFrame) -> pd.DataFrame:
    e = base_maestra[["SKU", "PESO_KG"]].copy()
    e["EXCEDE_CONSTANTE_NIOSH"] = e["PESO_KG"] > CONSTANTE_NIOSH_KG
    e["APTO_BANDA_ORO_FAVORABLE"] = e["PESO_KG"] <= RWL_FAVORABLE_KG
    e["APTO_BANDA_ORO_CONSERVADOR"] = e["PESO_KG"] <= RWL_CONSERVADOR_KG
    return e
