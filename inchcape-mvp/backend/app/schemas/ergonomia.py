from pydantic import BaseModel


class ErgonomiaSKU(BaseModel):
    SKU: str
    PESO_KG: float
    EXCEDE_CONSTANTE_NIOSH: bool
    APTO_BANDA_ORO_FAVORABLE: bool
    APTO_BANDA_ORO_CONSERVADOR: bool


class RespuestaErgonomia(BaseModel):
    banda_oro_cm: tuple[float, float]
    constante_niosh_kg: float
    rwl_favorable_kg: float
    rwl_conservador_kg: float
    skus: list[ErgonomiaSKU]
