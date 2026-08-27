from fastapi import APIRouter, HTTPException

from app.dominio.reglas.modelos import Regla
from app.dominio.reglas.repositorio import (
    ReglaDuplicadaError,
    ReglaNoEncontradaError,
    actualizar_regla,
    crear_regla,
    eliminar_regla,
    listar_reglas,
)

router = APIRouter(prefix="/reglas", tags=["reglas"])


@router.get("", response_model=list[Regla])
def listar() -> list[Regla]:
    return listar_reglas()


@router.post("", response_model=Regla, status_code=201)
def crear(regla: Regla) -> Regla:
    try:
        return crear_regla(regla)
    except ReglaDuplicadaError as e:
        raise HTTPException(409, detail=str(e)) from e


@router.put("/{id_regla}", response_model=Regla)
def actualizar(id_regla: str, regla: Regla) -> Regla:
    try:
        return actualizar_regla(id_regla, regla)
    except ReglaNoEncontradaError as e:
        raise HTTPException(404, detail=str(e)) from e


@router.delete("/{id_regla}", status_code=204)
def eliminar(id_regla: str) -> None:
    try:
        eliminar_regla(id_regla)
    except ReglaNoEncontradaError as e:
        raise HTTPException(404, detail=str(e)) from e
