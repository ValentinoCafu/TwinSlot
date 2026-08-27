from pydantic import BaseModel


class SolicitudPipeline(BaseModel):
    pesos_score: dict[str, float] | None = None
    porcentaje_max_movimiento: float | None = None


class RecomendacionSKU(BaseModel):
    RANKING_SCORE: int
    SKU: str
    MARCA: str
    FAMILIA: str
    ABC: str
    ROTACION_6M: float
    N_PEDIDOS: float
    N_LINEAS: float
    CANT_TOTAL: float
    VOLUMEN_M3: float
    PESO_KG: float
    ZONA_ACTUAL: str
    ZONA_RECOMENDADA: str
    TIEMPO_LAYOUT_ACTUAL: float
    TIEMPO_NUEVO_MIN: float
    COSTO_ACTUAL_MIN: float
    COSTO_NUEVO_MIN: float
    AHORRO_ESTIMADO_MIN: float
    AHORRO_PORCENTAJE: float
    SCORE_PRIORIDAD: float
    MOVIMIENTO: str
    JUSTIFICACION: str
    CLUSTER_ML: int
    PERFIL_ML: str
    PRIORIDAD_CLUSTER_RANK: int
    INDICE_IMPACTO_CLUSTER: float

    model_config = {"populate_by_name": True}


class Kpis(BaseModel):
    sku_analizados: int
    sku_movidos: int
    porcentaje_sku_movidos: float
    max_movimientos_permitidos: int
    tiempo_actual_min: float
    tiempo_optimizado_min: float
    ahorro_min: float
    reduccion_porcentaje: float
    productividad_actual_lineas_hh: float
    productividad_optimizada_lineas_hh: float
    tiempo_promedio_actual_min_pedido: float
    tiempo_promedio_optimizado_min_pedido: float


class DecisionRegla(BaseModel):
    sku: str
    regla_id: str
    motivo: str


class MetricasML(BaseModel):
    mejor_k: int
    silhouette: float
    interpretacion_silhouette: str
    variables_usadas: list[str]
    # dict, no un modelo rígido: las columnas son las medias por variable
    # de `variables_usadas`, que varían según qué atributos tengan
    # variación en el lote -- es justo el "perfil de centroide en
    # variables reales" que pide la explicabilidad (no una lista fija).
    perfil_clusters: list[dict]


class RespuestaPipeline(BaseModel):
    recomendaciones: list[RecomendacionSKU]
    kpis: Kpis
    banderas_activas: dict[str, bool]
    camino_decision_reglas: list[DecisionRegla]
    ml: MetricasML
