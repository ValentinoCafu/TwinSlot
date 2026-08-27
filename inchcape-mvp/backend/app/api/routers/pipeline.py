import json

from fastapi import APIRouter, HTTPException
from sqlalchemy import delete, insert

from app.core.db import engine, leer_tablas_lote, resultados_ultimo_lote
from app.core.flags import evaluar_banderas
from app.dominio.optimizador import OptimizadorInfactibleError
from app.dominio.pipeline import SinLoteIngeridoError, ejecutar_pipeline
from app.dominio.recomendaciones import FactibilidadError
from app.dominio.reglas.repositorio import listar_reglas
from app.schemas.pipeline import Kpis, MetricasML, RespuestaPipeline, SolicitudPipeline

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/ejecutar", response_model=RespuestaPipeline)
def ejecutar(solicitud: SolicitudPipeline | None = None) -> RespuestaPipeline:
    """Corre indicadores -> impacto -> score -> capacidad -> optimizador
    -> recomendaciones -> KPIs sobre el lote vigente (el último
    `POST /ingesta` exitoso), y persiste el resultado.
    """
    solicitud = solicitud or SolicitudPipeline()
    datasets = leer_tablas_lote()
    reglas = listar_reglas()
    try:
        resultado = ejecutar_pipeline(
            datasets, solicitud.pesos_score, solicitud.porcentaje_max_movimiento, reglas
        )
    except SinLoteIngeridoError as e:
        raise HTTPException(422, detail=str(e)) from e
    except (OptimizadorInfactibleError, FactibilidadError) as e:
        raise HTTPException(409, detail=str(e)) from e

    _persistir_resultado(resultado.recomendaciones)

    filas = resultado.recomendaciones.rename(columns={"AHORRO_%": "AHORRO_PORCENTAJE"}).to_dict("records")
    return RespuestaPipeline(
        recomendaciones=filas,
        kpis=Kpis(**resultado.kpis),
        banderas_activas=evaluar_banderas(),
        camino_decision_reglas=resultado.camino_decision_reglas,
        ml=MetricasML(
            mejor_k=resultado.ml.mejor_k,
            silhouette=resultado.ml.silhouette,
            interpretacion_silhouette=resultado.ml.interpretacion_silhouette,
            variables_usadas=resultado.ml.variables_usadas,
            perfil_clusters=resultado.ml.perfil_clusters.to_dict("records"),
        ),
    )


def _persistir_resultado(recomendaciones) -> None:
    with engine.begin() as conn:
        conn.execute(delete(resultados_ultimo_lote))
        conn.execute(
            insert(resultados_ultimo_lote),
            [
                {"SKU": fila["SKU"], "resultado_json": json.dumps(fila, ensure_ascii=False, default=str)}
                for fila in recomendaciones.to_dict("records")
            ],
        )
