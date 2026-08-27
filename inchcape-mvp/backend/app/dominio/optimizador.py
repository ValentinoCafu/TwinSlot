"""Fases 10 y 11 del notebook original -- Configuración y ejecución del
optimizador de asignación factible.

Puerto directo de `MVP_Reslotting_Inchcape.ipynb` (celdas 80-96). Variable
binaria x(sku, zona) = 1 si el SKU se asigna a esa zona. Minimiza tiempo
total de picking + penalización de movimiento, sujeto a:

  - una zona por SKU,
  - capacidad de cada zona (ocupación base no modelada + volumen asignado),
  - tope de SKU movidos (`porcentaje_max_movimiento`),
  - zonas bloqueadas como destino nuevo (`zonas_no_destino`),
  - reglas duras del motor de reglas (`zona_unica_por_sku`,
    `zonas_excluidas_por_sku`, `pares_familias_incompatibles`) --
    ninguna regla de seguridad es negociable por un buen score, así que
    se aplican como variables fijadas, no como término del objetivo.
"""

from __future__ import annotations

from dataclasses import dataclass
import shutil

import pandas as pd
import pulp


class OptimizadorInfactibleError(RuntimeError):
    """El solver no encontró una solución óptima -- revisar capacidades
    y restricciones antes de confiar en el resultado."""


@dataclass
class ResultadoOptimizador:
    estado: str
    valor_objetivo: float
    zona_asignada: dict[str, str]  # SKU -> ZONA (nueva asignación óptima)
    max_movimientos: int


def ejecutar_optimizador(
    base_maestra: pd.DataFrame,
    layout_cd: pd.DataFrame,
    capacidad: pd.DataFrame,
    porcentaje_max_movimiento: float,
    zonas_no_destino: list[str] | None = None,
    penalizacion_movimiento: float = 0.0,
    zona_unica_por_sku: dict[str, str] | None = None,
    zonas_excluidas_por_sku: dict[str, set[str]] | None = None,
    pares_familias_incompatibles: list[tuple[str, str]] | None = None,
) -> ResultadoOptimizador:
    zonas_no_destino = zonas_no_destino or []
    zona_unica_por_sku = zona_unica_por_sku or {}
    zonas_excluidas_por_sku = zonas_excluidas_por_sku or {}
    pares_familias_incompatibles = pares_familias_incompatibles or []

    lista_skus = base_maestra["SKU"].tolist()
    lista_zonas = layout_cd["ZONA"].tolist()

    volumen_sku = base_maestra.set_index("SKU")["VOLUMEN_M3"].to_dict()
    frecuencia_sku = base_maestra.set_index("SKU")["N_LINEAS"].to_dict()
    zona_actual_sku = base_maestra.set_index("SKU")["ZONA_ACTUAL"].to_dict()
    tiempo_zona = layout_cd.set_index("ZONA")["TIEMPO_MINUTOS"].to_dict()
    capacidad_max = capacidad.set_index("ZONA")["CAPACIDAD_MAX_M3"].to_dict()
    ocupacion_no_modelada = capacidad.set_index("ZONA")["VOLUMEN_BASE_NO_MODELADO"].to_dict()

    max_movimientos = max(1, round(len(base_maestra) * porcentaje_max_movimiento))

    modelo = pulp.LpProblem("Optimizacion_Reslotting_CD_Aldeas", pulp.LpMinimize)
    x = pulp.LpVariable.dicts("Asignacion", (lista_skus, lista_zonas), lowBound=0, upBound=1, cat="Binary")

    costo_picking = pulp.lpSum(
        frecuencia_sku[sku] * tiempo_zona[zona] * x[sku][zona] for sku in lista_skus for zona in lista_zonas
    )
    costo_movimientos = pulp.lpSum(
        penalizacion_movimiento * x[sku][zona]
        for sku in lista_skus
        for zona in lista_zonas
        if zona != zona_actual_sku[sku]
    )
    modelo += costo_picking + costo_movimientos

    # Una zona por SKU
    for sku in lista_skus:
        modelo += pulp.lpSum(x[sku][zona] for zona in lista_zonas) == 1

    # Capacidad por zona
    for zona in lista_zonas:
        modelo += (
            ocupacion_no_modelada.get(zona, 0)
            + pulp.lpSum(volumen_sku[sku] * x[sku][zona] for sku in lista_skus)
            <= capacidad_max[zona]
        )

    # Tope de movimientos
    modelo += (
        pulp.lpSum(x[sku][zona] for sku in lista_skus for zona in lista_zonas if zona != zona_actual_sku[sku])
        <= max_movimientos
    )

    # Zonas bloqueadas como destino nuevo (un SKU ya presente puede quedarse)
    for zona in zonas_no_destino:
        if zona not in lista_zonas:
            continue
        for sku in lista_skus:
            if zona_actual_sku[sku] != zona:
                modelo += x[sku][zona] == 0

    # Regla de atributo: zona única forzada por una condición del SKU
    for sku, zona in zona_unica_por_sku.items():
        if sku in lista_skus and zona in lista_zonas:
            modelo += x[sku][zona] == 1

    # Regla de atributo: zona explícitamente prohibida para el SKU
    for sku, zonas_prohibidas in zonas_excluidas_por_sku.items():
        for zona in zonas_prohibidas & set(lista_zonas):
            if sku in lista_skus:
                modelo += x[sku][zona] == 0

    # Regla de incompatibilidad: dos familias no pueden compartir zona.
    # y[familia][zona] = 1 si algún SKU de esa familia queda en esa zona;
    # se fuerza vía x[sku][zona] <= y[familia][zona], y luego se prohíbe
    # que dos familias incompatibles tengan ambas y=1 en la misma zona.
    if pares_familias_incompatibles:
        familia_sku = base_maestra.set_index("SKU")["FAMILIA"].to_dict()
        familias_en_conflicto = {f for par in pares_familias_incompatibles for f in par}
        y = pulp.LpVariable.dicts(
            "FamiliaEnZona", (list(familias_en_conflicto), lista_zonas), lowBound=0, upBound=1, cat="Binary"
        )
        for sku in lista_skus:
            familia = familia_sku.get(sku)
            if familia not in familias_en_conflicto:
                continue
            for zona in lista_zonas:
                modelo += x[sku][zona] <= y[familia][zona]

        for familia_a, familia_b in pares_familias_incompatibles:
            for zona in lista_zonas:
                modelo += y[familia_a][zona] + y[familia_b][zona] <= 1

    ruta_cbc = shutil.which("cbc") or pulp.PULP_CBC_CMD(msg=False).path
    solver = pulp.COIN_CMD(path=ruta_cbc, msg=False)
    modelo.solve(solver)
    estado = pulp.LpStatus[modelo.status]

    if estado != "Optimal":
        raise OptimizadorInfactibleError(
            f"El optimizador no encontró una solución óptima (estado: {estado}). "
            "Revisar capacidades y restricciones."
        )

    zona_asignada = {sku: zona for sku in lista_skus for zona in lista_zonas if x[sku][zona].value() == 1}

    return ResultadoOptimizador(
        estado=estado,
        valor_objetivo=pulp.value(modelo.objective),
        zona_asignada=zona_asignada,
        max_movimientos=max_movimientos,
    )
