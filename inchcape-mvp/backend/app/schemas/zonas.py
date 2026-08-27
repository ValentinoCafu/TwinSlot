from pydantic import BaseModel


class Zona(BaseModel):
    id: str
    nombre: str
    clave_excel: str
    distancia_m: float
    ubicaciones: str
    lineas_picking: int
    color: str
    puntos_svg: str
    label_x: float
    label_y: float
    label_fs: float
    label_rot: float
    texto_claro: bool


class RespuestaZonas(BaseModel):
    zonas: list[Zona]
    distancia_absoluta_confirmada: bool = False
