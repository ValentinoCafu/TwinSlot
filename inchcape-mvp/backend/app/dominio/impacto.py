"""Fases 4, 5 y 6 del notebook original -- Base Maestra, impacto
operativo y análisis ABC vs. impacto.

Puerto directo de `MVP_Reslotting_Inchcape.ipynb` (celdas 32-52). Los
`assert` del notebook (que abortarían todo el proceso Python si fallan)
se convierten aquí en `ValueError` explícitos capturables por el router
de FastAPI -- una fila con datos corruptos debe devolver un 422 con el
detalle, no tumbar el servidor.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


class BaseMaestraInvalidaError(ValueError):
    """La integración de fuentes produjo una Base Maestra inconsistente."""


def construir_base_maestra(
    sku_maestro: pd.DataFrame,
    rotacion: pd.DataFrame,
    stock_actual: pd.DataFrame,
    pedidos_por_sku: pd.DataFrame,
    layout_cd: pd.DataFrame,
) -> pd.DataFrame:
    """Fase 4 -- integra Maestro + Rotación + Stock + indicadores de
    pedidos + layout de la zona actual, todo unido por SKU / ZONA_ACTUAL.
    """
    base_maestra = sku_maestro.merge(rotacion, on="SKU", how="left").merge(stock_actual, on="SKU", how="left")

    base_maestra = base_maestra.merge(pedidos_por_sku, on="SKU", how="left")
    columnas_pedido = [
        "N_LINEAS",
        "N_PEDIDOS",
        "CANT_TOTAL",
        "CANT_PROMEDIO",
        "TIEMPO_OBSERVADO_PROM",
        "TIEMPO_OBSERVADO_TOTAL",
        "UNIDADES_POR_PEDIDO",
    ]
    base_maestra[columnas_pedido] = base_maestra[columnas_pedido].fillna(0)

    layout_actual = layout_cd.rename(
        columns={
            "ZONA": "ZONA_ACTUAL",
            "DISTANCIA_METROS": "DISTANCIA_ACTUAL_M",
            "TIEMPO_MINUTOS": "TIEMPO_LAYOUT_ACTUAL",
            "CAPACIDAD_M3_MAX": "CAPACIDAD_ZONA_ACTUAL",
        }
    )
    base_maestra = base_maestra.merge(layout_actual, on="ZONA_ACTUAL", how="left")

    _validar_base_maestra(base_maestra)
    return base_maestra


def _validar_base_maestra(base_maestra: pd.DataFrame) -> None:
    if base_maestra["SKU"].nunique() != len(base_maestra):
        raise BaseMaestraInvalidaError(
            f"SKU duplicado tras la integración: {len(base_maestra)} filas, "
            f"{base_maestra['SKU'].nunique()} SKU únicos."
        )
    sin_zona = base_maestra[base_maestra["ZONA_ACTUAL"].isna()]
    if len(sin_zona):
        raise BaseMaestraInvalidaError(
            f"{len(sin_zona)} SKU sin ZONA_ACTUAL tras el cruce con stock: " f"{sin_zona['SKU'].tolist()}"
        )
    sin_tiempo = base_maestra[base_maestra["TIEMPO_LAYOUT_ACTUAL"].isna()]
    if len(sin_tiempo):
        raise BaseMaestraInvalidaError(
            f"{len(sin_tiempo)} SKU cuya ZONA_ACTUAL no aparece en layout_cd: "
            f"{sin_tiempo[['SKU', 'ZONA_ACTUAL']].to_dict('records')}"
        )


@dataclass
class ImpactoOperativo:
    base_maestra: pd.DataFrame
    tiempo_minimo_cd: float
    zona_mas_rapida: str


def calcular_impacto_operativo(base_maestra: pd.DataFrame, layout_cd: pd.DataFrame) -> ImpactoOperativo:
    """Fase 5 -- Carga Operativa = N_LINEAS × tiempo de acceso actual.
    Ahorro Teórico = N_LINEAS × (tiempo actual − tiempo mínimo del CD).

    `tiempo_minimo_cd` es una referencia para el techo del ahorro
    potencial, no una zona destino garantizada -- el notebook original ya
    aclara esto en 5.2, se mantiene el mismo comentario aquí.
    """
    base_maestra = base_maestra.copy()
    base_maestra["CARGA_OPERATIVA_MIN"] = base_maestra["N_LINEAS"] * base_maestra["TIEMPO_LAYOUT_ACTUAL"]

    fila_zona_rapida = layout_cd.sort_values("TIEMPO_MINUTOS").iloc[0]
    tiempo_minimo_cd = float(layout_cd["TIEMPO_MINUTOS"].min())

    base_maestra["AHORRO_TEORICO_MIN"] = (
        base_maestra["N_LINEAS"] * (base_maestra["TIEMPO_LAYOUT_ACTUAL"] - tiempo_minimo_cd)
    ).clip(lower=0)

    return ImpactoOperativo(
        base_maestra=base_maestra,
        tiempo_minimo_cd=tiempo_minimo_cd,
        zona_mas_rapida=str(fila_zona_rapida["ZONA"]),
    )


def ranking_preliminar(base_maestra: pd.DataFrame) -> pd.DataFrame:
    """Fase 5.4 -- ranking descendente por ahorro teórico."""
    ranking = base_maestra.sort_values("AHORRO_TEORICO_MIN", ascending=False).reset_index(drop=True)
    ranking["RANKING_PRELIMINAR"] = ranking.index + 1
    return ranking


def identificar_top_sku(ranking: pd.DataFrame, porcentaje_top: float) -> pd.DataFrame:
    """Fase 5.5 -- el % superior por ahorro teórico, nunca un conteo
    hardcodeado ("20 SKU") -- se deriva del tamaño real del catálogo.
    """
    cantidad_top = max(1, round(len(ranking) * porcentaje_top))
    top_sku = ranking.head(cantidad_top).copy()
    top_sku["CANDIDATO_INICIAL"] = "SÍ"
    return top_sku


def analisis_abc(base_maestra: pd.DataFrame) -> pd.DataFrame:
    """Fase 6.1 -- ¿la clase ABC (rotación declarada) explica por sí sola
    la carga/el ahorro? (Ya se sabe que no del todo: CLAUDE_1.md punto 5,
    χ² ABC vs. ZONA_ACTUAL p=0.646 sobre este mismo dataset.)
    """
    return (
        base_maestra.groupby("ABC")
        .agg(
            SKU=("SKU", "count"),
            ROTACION_PROMEDIO=("ROTACION_6M", "mean"),
            VISITAS_PROMEDIO=("N_LINEAS", "mean"),
            CARGA_PROMEDIO=("CARGA_OPERATIVA_MIN", "mean"),
            AHORRO_PROMEDIO=("AHORRO_TEORICO_MIN", "mean"),
        )
        .reset_index()
    )


def distribucion_top_abc(top_sku: pd.DataFrame) -> pd.DataFrame:
    """Fase 6.2 -- si aparecen SKU B/C en el TOP, ABC solo no basta."""
    return top_sku["ABC"].value_counts().rename_axis("ABC").reset_index(name="CANTIDAD_SKU")
