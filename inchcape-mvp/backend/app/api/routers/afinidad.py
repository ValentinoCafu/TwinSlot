import pandas as pd
from fastapi import APIRouter, HTTPException

from app.core.db import engine
from app.dominio.afinidad import (
    calcular_significancia_afinidad,
    conjuntos_frecuentes,
    construir_pares_coocurrencia,
)
from app.schemas.afinidad import RespuestaAfinidad

router = APIRouter(prefix="/afinidad", tags=["afinidad"])

MAX_PARES_DEVUELTOS = 30


@router.get("", response_model=RespuestaAfinidad)
def obtener_afinidad() -> RespuestaAfinidad:
    """Motor de afinidad ejecutado en vivo sobre el lote vigente: pares
    (Lift/Jaccard) + conjuntos frecuentes (N>=3) + test de significancia
    por remuestreo (200 réplicas) que decide si hay señal real -- nunca
    se activa por opinión (ver `dominio/afinidad.py`).
    """
    with engine.connect() as conn:
        pedidos = pd.read_sql("SELECT * FROM pedidos", conn)
    if pedidos.empty:
        raise HTTPException(422, detail="No hay un lote ingerido. Llama POST /ingesta primero.")

    pares = construir_pares_coocurrencia(pedidos)
    test = calcular_significancia_afinidad(pedidos)
    itemsets = conjuntos_frecuentes(pedidos)

    motivo = (
        f"Modularidad observada ({test.modularidad_observada:.3f}) supera el percentil 95 "
        f"del nulo por remuestreo ({test.percentil_95_nulo:.3f})."
        if test.usar_afinidad
        else (
            f"Sin señal de afinidad suficiente (n={pedidos['SKU'].nunique()} SKU, "
            f"{pedidos['PEDIDO_ID'].nunique()} pedidos): modularidad observada "
            f"({test.modularidad_observada:.3f}) no supera el percentil 95 del nulo "
            f"({test.percentil_95_nulo:.3f}). Score usa solo velocidad + ergonomía."
        )
    )

    return RespuestaAfinidad(
        activo=test.usar_afinidad,
        motivo=motivo,
        test_significancia={
            "modularidad_observada": test.modularidad_observada,
            "media_nula": test.media_nula,
            "percentil_95_nulo": test.percentil_95_nulo,
            "n_replicas": test.n_replicas,
        },
        pares=pares.head(MAX_PARES_DEVUELTOS).to_dict("records"),
        conjuntos_frecuentes=itemsets.to_dict("records"),
    )
