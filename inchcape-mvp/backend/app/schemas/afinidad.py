from pydantic import BaseModel


class ParAfinidad(BaseModel):
    SKU_A: str
    SKU_B: str
    N_COOCURRENCIA: int
    SOPORTE: float
    LIFT: float
    JACCARD: float


class ConjuntoFrecuente(BaseModel):
    ITEMSET: str
    N_ITEMS: int
    FRECUENCIA: int
    SOPORTE: float


class TestSignificancia(BaseModel):
    modularidad_observada: float
    media_nula: float
    percentil_95_nulo: float
    n_replicas: int


class RespuestaAfinidad(BaseModel):
    activo: bool
    motivo: str
    test_significancia: TestSignificancia
    pares: list[ParAfinidad]
    conjuntos_frecuentes: list[ConjuntoFrecuente]
