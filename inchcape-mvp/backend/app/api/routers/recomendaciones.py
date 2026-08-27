from fastapi import APIRouter, HTTPException

from app.core.config import PESOS_SCORE
from app.core.db import leer_tablas_lote
from app.dominio.ml_perfil import explicar_sku
from app.dominio.optimizador import OptimizadorInfactibleError
from app.dominio.pipeline import SinLoteIngeridoError, ejecutar_pipeline
from app.dominio.recomendaciones import FactibilidadError
from app.dominio.reglas.repositorio import listar_reglas
from app.schemas.pipeline import DecisionRegla, RecomendacionSKU
from app.schemas.recomendaciones import DesgloseScore, ExplicacionCluster, RespuestaRecomendacionSKU

router = APIRouter(prefix="/recomendaciones", tags=["recomendaciones"])


@router.get("/{sku}", response_model=RespuestaRecomendacionSKU)
def detalle_sku(sku: str) -> RespuestaRecomendacionSKU:
    """Panel de explicabilidad completo de un SKU: score desglosado por
    criterio, reglas que lo afectaron, y el cluster ML explicado
    (contribución por variable, distancia a centroides, silhouette
    individual) -- las piezas que pide
    `propuesta-motor-reglas-y-explicabilidad.md` §5 para que la
    recomendación nunca sea una caja negra.

    Recorre el pipeline completo con los parámetros por defecto -- no
    hay estado cacheado entre requests, coherente con el resto del
    backend (ver plan-desarrollo-mvp-react-fastapi.md).
    """
    datasets = leer_tablas_lote()
    reglas = listar_reglas()
    try:
        resultado = ejecutar_pipeline(datasets, reglas=reglas)
    except SinLoteIngeridoError as e:
        raise HTTPException(422, detail=str(e)) from e
    except (OptimizadorInfactibleError, FactibilidadError) as e:
        raise HTTPException(409, detail=str(e)) from e

    fila_rec = resultado.recomendaciones.loc[resultado.recomendaciones["SKU"] == sku]
    if fila_rec.empty:
        raise HTTPException(404, detail=f"SKU '{sku}' no existe en el lote vigente")
    recomendacion = fila_rec.iloc[0].rename({"AHORRO_%": "AHORRO_PORCENTAJE"}).to_dict()

    fila_base = resultado.ml.base_con_ml.set_index("SKU").loc[sku]
    ahorro = PESOS_SCORE["ahorro"] * fila_base["AHORRO_NORM"] * 100
    rotacion = PESOS_SCORE["rotacion"] * fila_base["ROTACION_NORM"] * 100
    abc = PESOS_SCORE["abc"] * fila_base["ABC_SCORE"] * 100
    facilidad = PESOS_SCORE["facilidad_movimiento"] * fila_base["FACILIDAD_MOVIMIENTO"] * 100

    reglas_aplicadas = [d for d in resultado.camino_decision_reglas if d["sku"] == sku]

    return RespuestaRecomendacionSKU(
        recomendacion=RecomendacionSKU(**recomendacion),
        desglose_score=DesgloseScore(
            ahorro=ahorro,
            rotacion=rotacion,
            abc=abc,
            facilidad_movimiento=facilidad,
            total=ahorro + rotacion + abc + facilidad,
        ),
        reglas_aplicadas=[DecisionRegla(**d) for d in reglas_aplicadas],
        explicacion_cluster=ExplicacionCluster(**explicar_sku(sku, resultado.ml)),
    )
