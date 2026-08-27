from pydantic import BaseModel

from app.schemas.pipeline import DecisionRegla, RecomendacionSKU


class DesgloseScore(BaseModel):
    ahorro: float
    rotacion: float
    abc: float
    facilidad_movimiento: float
    total: float


class ExplicacionCluster(BaseModel):
    cluster: int
    perfil: str
    distancia_cluster_propio: float
    distancia_segundo_mas_cercano: float
    asignacion_ambigua: bool
    silhouette_individual: float
    contribucion_por_variable: dict[str, float]


class RespuestaRecomendacionSKU(BaseModel):
    recomendacion: RecomendacionSKU
    desglose_score: DesgloseScore
    reglas_aplicadas: list[DecisionRegla]
    explicacion_cluster: ExplicacionCluster
