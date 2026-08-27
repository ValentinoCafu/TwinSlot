"""Fase 3 del notebook original -- construcción de indicadores por SKU.

Puerto directo de `MVP_Reslotting_Inchcape.ipynb` (celdas 24-30), con la
lógica de agregación intacta. Único cambio respecto al notebook: se
recibe `pedidos` como parámetro explícito en vez de depender de una
variable global de celda -- es justamente el riesgo de refactor señalado
en `plan-desarrollo-mvp-react-fastapi.md` §4.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def construir_pedidos_por_sku(pedidos: pd.DataFrame) -> pd.DataFrame:
    """Agrega la tabla de líneas de pedido (nivel línea) a nivel SKU.

    N_LINEAS se usa como aproximación a la frecuencia de visitas a la
    ubicación (hallazgo ya validado en CLAUDE_1.md punto 2: usar hits
    reales, no ROTACION_6M/ABC, como criterio de velocidad).
    """
    pedidos_por_sku = (
        pedidos.groupby("SKU")
        .agg(
            N_LINEAS=("SKU", "size"),
            N_PEDIDOS=("PEDIDO_ID", "nunique"),
            CANT_TOTAL=("CANTIDAD", "sum"),
            CANT_PROMEDIO=("CANTIDAD", "mean"),
            TIEMPO_OBSERVADO_PROM=("TIEMPO_HOY_MIN", "mean"),
            TIEMPO_OBSERVADO_TOTAL=("TIEMPO_HOY_MIN", "sum"),
        )
        .reset_index()
    )

    pedidos_por_sku["UNIDADES_POR_PEDIDO"] = np.where(
        pedidos_por_sku["N_PEDIDOS"] > 0,
        pedidos_por_sku["CANT_TOTAL"] / pedidos_por_sku["N_PEDIDOS"],
        0,
    )
    return pedidos_por_sku
