"""Las 3 categorías de regla dura ya definidas en
`propuesta-motor-reglas-y-explicabilidad.md` §2 (la 4ª, FIFO, no aplica
al dataset de práctica -- no existe fecha de lote).

Estos mismos modelos Pydantic sirven de esquema de API y de forma de
persistencia (serializados a `definicion_json` en la tabla `reglas`) --
una sola definición, no una capa de DTO paralela para un objeto que ya
es una configuración estructurada, no una tabla de datos.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, model_validator

Operador = Literal["==", "!=", ">", ">=", "<", "<="]


class ReglaAtributoDef(BaseModel):
    """Ej.: 'motores al piso' -- condición sobre un campo del SKU que
    fija o prohíbe una zona."""

    campo: str
    operador: Operador
    valor: float | str
    zona_permitida: str | None = None
    zona_prohibida: str | None = None


class ReglaIncompatibilidadDef(BaseModel):
    """Ej.: 'lubricantes lejos de baterías' -- dos familias no pueden
    compartir zona. Nivel 1: modo binario (misma zona sí/no); distancia
    mínima en metros queda para cuando la geometría absoluta esté
    confirmada (ver plan-desarrollo-mvp-react-fastapi.md §11)."""

    familia_a: str
    familia_b: str
    modo: Literal["misma_zona_prohibida"] = "misma_zona_prohibida"


class ReglaUmbralDef(BaseModel):
    """Ej.: 'no mover si el payback tarda más de X meses' -- filtro
    numérico configurable, nunca hardcodeado en el pipeline."""

    campo_evaluado: str
    operador: Operador
    valor_umbral: float
    accion: str


DefinicionRegla = ReglaAtributoDef | ReglaIncompatibilidadDef | ReglaUmbralDef

TIPO_A_MODELO: dict[str, type[BaseModel]] = {
    "atributo": ReglaAtributoDef,
    "incompatibilidad": ReglaIncompatibilidadDef,
    "umbral": ReglaUmbralDef,
}


class Regla(BaseModel):
    id: str
    tipo: Literal["atributo", "incompatibilidad", "umbral"]
    nombre: str
    definicion: DefinicionRegla
    activa: bool = True
    justificacion: str = ""

    @model_validator(mode="after")
    def _definicion_coincide_con_tipo(self) -> Regla:
        esperado = TIPO_A_MODELO[self.tipo]
        if not isinstance(self.definicion, esperado):
            raise ValueError(f"tipo='{self.tipo}' requiere una 'definicion' de forma {esperado.__name__}")
        return self
