import pandas as pd
from fastapi import APIRouter

from app.core.db import engine
from app.dominio.ergonomia import (
    BANDA_ORO_CM_MAX,
    BANDA_ORO_CM_MIN,
    CONSTANTE_NIOSH_KG,
    RWL_CONSERVADOR_KG,
    RWL_FAVORABLE_KG,
    calcular_ergonomia,
)
from app.schemas.ergonomia import RespuestaErgonomia

router = APIRouter(prefix="/ergonomia", tags=["ergonomia"])


@router.get("", response_model=RespuestaErgonomia)
def obtener_ergonomia() -> RespuestaErgonomia:
    """Banda de oro NIOSH sobre el lote vigente -- solo depende de
    PESO_KG (atributo estático del SKU), no requiere pipeline completo.
    """
    with engine.connect() as conn:
        sku_maestro = pd.read_sql("SELECT SKU, PESO_KG FROM sku_maestro", conn)
    resultado = calcular_ergonomia(sku_maestro)
    return RespuestaErgonomia(
        banda_oro_cm=(BANDA_ORO_CM_MIN, BANDA_ORO_CM_MAX),
        constante_niosh_kg=CONSTANTE_NIOSH_KG,
        rwl_favorable_kg=RWL_FAVORABLE_KG,
        rwl_conservador_kg=RWL_CONSERVADOR_KG,
        skus=resultado.to_dict("records"),
    )
