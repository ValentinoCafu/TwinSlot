from fastapi import APIRouter
from sqlalchemy import select

from app.core.db import engine
from app.core.db import zonas as tbl_zonas
from app.schemas.zonas import RespuestaZonas

router = APIRouter(prefix="/zonas", tags=["zonas"])


@router.get("", response_model=RespuestaZonas)
def listar_zonas() -> RespuestaZonas:
    """Geometría de las 13 zonas del plano vectorial, portada de
    `V1 planta-cd-aldeas-vectorial.html`. La escala y el punto I/O son
    supuestos declarados, no medidos -- de ahí `distancia_absoluta_confirmada`
    (ver `plan-desarrollo-mvp-react-fastapi.md` §4).
    """
    with engine.connect() as conn:
        filas = conn.execute(select(tbl_zonas)).mappings().all()
    return RespuestaZonas(zonas=list(filas), distancia_absoluta_confirmada=False)
