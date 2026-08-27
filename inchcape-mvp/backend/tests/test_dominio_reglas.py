import pandas as pd
import pytest
from pydantic import ValidationError

from app.dominio.reglas.evaluador import (
    aplicar_reglas_atributo,
    evaluar_umbral,
    pares_familias_incompatibles,
)
from app.dominio.reglas.modelos import (
    Regla,
    ReglaAtributoDef,
    ReglaIncompatibilidadDef,
    ReglaUmbralDef,
)
from app.dominio.reglas.repositorio import (
    ReglaDuplicadaError,
    ReglaNoEncontradaError,
    actualizar_regla,
    crear_regla,
    eliminar_regla,
    listar_reglas,
)


def _regla_atributo(**kw) -> Regla:
    base = dict(campo="PESO_KG", operador=">", valor=30, zona_prohibida="Multinivel Cluster")
    base.update(kw)
    return Regla(
        id="R-TEST-1", tipo="atributo", nombre="Pesados fuera de cluster", definicion=ReglaAtributoDef(**base)
    )


def test_regla_rechaza_definicion_que_no_coincide_con_tipo():
    with pytest.raises(ValidationError):
        Regla(
            id="R-X",
            tipo="atributo",
            nombre="mal formada",
            definicion=ReglaIncompatibilidadDef(familia_a="A", familia_b="B"),
        )


def test_aplicar_reglas_atributo_excluye_zona_para_skus_que_cumplen():
    base = pd.DataFrame({"SKU": ["A", "B"], "PESO_KG": [40, 5]})
    resultado = aplicar_reglas_atributo(base, [_regla_atributo()])

    assert resultado.zonas_excluidas_por_sku == {"A": {"Multinivel Cluster"}}
    assert "B" not in resultado.zonas_excluidas_por_sku
    assert resultado.camino_decision[0]["sku"] == "A"
    assert resultado.camino_decision[0]["regla_id"] == "R-TEST-1"


def test_aplicar_reglas_atributo_zona_permitida_fuerza_zona_unica():
    base = pd.DataFrame({"SKU": ["A"], "FAMILIA": ["Correas"]})
    regla = Regla(
        id="R-TEST-2",
        tipo="atributo",
        nombre="Correas al piso",
        definicion=ReglaAtributoDef(campo="FAMILIA", operador="==", valor="Correas", zona_permitida="Bulk"),
    )
    resultado = aplicar_reglas_atributo(base, [regla])
    assert resultado.zona_unica_por_sku == {"A": "Bulk"}


def test_regla_inactiva_no_se_aplica():
    base = pd.DataFrame({"SKU": ["A"], "PESO_KG": [40]})
    regla = _regla_atributo()
    regla_inactiva = regla.model_copy(update={"activa": False})
    resultado = aplicar_reglas_atributo(base, [regla_inactiva])
    assert resultado.zonas_excluidas_por_sku == {}


def test_pares_familias_incompatibles_solo_regla_incompatibilidad_activa():
    r1 = Regla(
        id="R-INC-1",
        tipo="incompatibilidad",
        nombre="Lubricantes lejos de Filtros",
        definicion=ReglaIncompatibilidadDef(familia_a="Lubricantes", familia_b="Filtros"),
    )
    r2 = _regla_atributo()  # de otro tipo, no debe aparecer
    assert pares_familias_incompatibles([r1, r2]) == [("Lubricantes", "Filtros")]
    assert pares_familias_incompatibles([r1.model_copy(update={"activa": False})]) == []


def test_evaluar_umbral():
    regla = Regla(
        id="R-UMB-1",
        tipo="umbral",
        nombre="Payback máximo",
        definicion=ReglaUmbralDef(
            campo_evaluado="PAYBACK_ESTIMADO", operador="<=", valor_umbral=3, accion="no mover"
        ),
    )
    assert evaluar_umbral(2.5, regla) is True
    assert evaluar_umbral(4, regla) is False


# ---------------------------------------------------------------------
# repositorio.py -- persistencia real (usa la BD de prueba de conftest)
# ---------------------------------------------------------------------


def test_repositorio_crud_roundtrip():
    regla = _regla_atributo()
    regla_id = regla.id
    try:
        eliminar_regla(regla_id)
    except ReglaNoEncontradaError:
        pass

    crear_regla(regla)
    with pytest.raises(ReglaDuplicadaError):
        crear_regla(regla)

    leidas = listar_reglas()
    assert any(r.id == regla_id for r in leidas)

    actualizada = regla.model_copy(update={"nombre": "Renombrada"})
    actualizar_regla(regla_id, actualizada)
    assert next(r for r in listar_reglas() if r.id == regla_id).nombre == "Renombrada"

    eliminar_regla(regla_id)
    assert all(r.id != regla_id for r in listar_reglas())
    with pytest.raises(ReglaNoEncontradaError):
        eliminar_regla(regla_id)
