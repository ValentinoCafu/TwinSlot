from typing import Any

from pydantic import BaseModel


class FilaRechazada(BaseModel):
    tabla: str
    fila: int
    motivo: str
    datos: dict[str, Any] | None = None


class ResumenTabla(BaseModel):
    aceptadas: int
    rechazadas: int


class RespuestaIngesta(BaseModel):
    filas_aceptadas: int
    filas_rechazadas: list[FilaRechazada]
    resumen_por_tabla: dict[str, ResumenTabla]
