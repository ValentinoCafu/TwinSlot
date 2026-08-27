"""Persistencia de reglas -- serializa/deserializa `Regla.definicion` a
la columna `definicion_json` de la tabla `reglas` (esquema ya creado en
Bloque 1, ver `core/db.py`)."""

from __future__ import annotations

from sqlalchemy import delete, insert, select, update

from app.core.db import engine
from app.core.db import reglas as tbl_reglas
from app.dominio.reglas.modelos import TIPO_A_MODELO, Regla


class ReglaNoEncontradaError(LookupError):
    pass


class ReglaDuplicadaError(ValueError):
    pass


def _fila_a_regla(fila) -> Regla:
    modelo = TIPO_A_MODELO[fila.tipo]
    return Regla(
        id=fila.id,
        tipo=fila.tipo,
        nombre=fila.nombre,
        definicion=modelo.model_validate_json(fila.definicion_json),
        activa=bool(fila.activa),
        justificacion=fila.justificacion or "",
    )


def _regla_a_fila(regla: Regla) -> dict:
    return {
        "id": regla.id,
        "tipo": regla.tipo,
        "nombre": regla.nombre,
        "definicion_json": regla.definicion.model_dump_json(),
        "activa": regla.activa,
        "justificacion": regla.justificacion,
    }


def listar_reglas() -> list[Regla]:
    with engine.connect() as conn:
        filas = conn.execute(select(tbl_reglas)).all()
    return [_fila_a_regla(f) for f in filas]


def crear_regla(regla: Regla) -> Regla:
    with engine.begin() as conn:
        existe = conn.execute(select(tbl_reglas.c.id).where(tbl_reglas.c.id == regla.id)).first()
        if existe:
            raise ReglaDuplicadaError(f"Ya existe una regla con id '{regla.id}'")
        conn.execute(insert(tbl_reglas), _regla_a_fila(regla))
    return regla


def actualizar_regla(id_regla: str, regla: Regla) -> Regla:
    with engine.begin() as conn:
        existe = conn.execute(select(tbl_reglas.c.id).where(tbl_reglas.c.id == id_regla)).first()
        if not existe:
            raise ReglaNoEncontradaError(f"No existe una regla con id '{id_regla}'")
        conn.execute(update(tbl_reglas).where(tbl_reglas.c.id == id_regla).values(**_regla_a_fila(regla)))
    return regla


def eliminar_regla(id_regla: str) -> None:
    with engine.begin() as conn:
        resultado = conn.execute(delete(tbl_reglas).where(tbl_reglas.c.id == id_regla))
        if resultado.rowcount == 0:
            raise ReglaNoEncontradaError(f"No existe una regla con id '{id_regla}'")
