"""Pruebas de scoring.py, matriz_sku_zona.py, capacidad.py y
optimizador.py (Fases 7-11) contra el dataset de práctica real, más
casos sintéticos pequeños para los caminos de error.
"""

import pandas as pd
import pytest

from app.core.config import MAPA_ABC_SCORE, PESOS_SCORE, PORCENTAJE_MAX_MOVIMIENTO
from app.core.db import engine
from app.dominio.capacidad import calcular_capacidad
from app.dominio.impacto import calcular_impacto_operativo, construir_base_maestra
from app.dominio.indicadores import construir_pedidos_por_sku
from app.dominio.matriz_sku_zona import (
    MatrizSkuZonaInvalidaError,
    construir_matriz_sku_zona,
    mejor_zona_teorica,
)
from app.dominio.optimizador import OptimizadorInfactibleError, ejecutar_optimizador
from app.dominio.scoring import calcular_score_prioridad, normalizar_01
from app.ingesta.mapeo import cargar_config_mapeo
from app.ingesta.servicio import procesar_workbook


@pytest.fixture(scope="module")
def pipeline_real(excel_practica_bytes):
    procesar_workbook(excel_practica_bytes, cargar_config_mapeo())
    with engine.connect() as conn:
        sku_maestro = pd.read_sql("SELECT * FROM sku_maestro", conn)
        rotacion = pd.read_sql("SELECT * FROM rotacion", conn)
        stock_actual = pd.read_sql("SELECT * FROM stock_actual", conn)
        layout_cd = pd.read_sql("SELECT * FROM layout_cd", conn)
        ocupacion_zona = pd.read_sql("SELECT * FROM ocupacion_zona", conn)
        pedidos = pd.read_sql("SELECT * FROM pedidos", conn)

    pedidos_por_sku = construir_pedidos_por_sku(pedidos)
    base = construir_base_maestra(sku_maestro, rotacion, stock_actual, pedidos_por_sku, layout_cd)
    impacto = calcular_impacto_operativo(base, layout_cd)
    base_con_score = calcular_score_prioridad(impacto.base_maestra, PESOS_SCORE, MAPA_ABC_SCORE)
    capacidad = calcular_capacidad(base_con_score, ocupacion_zona)
    return base_con_score, layout_cd, capacidad


# ---------------------------------------------------------------------
# scoring.py
# ---------------------------------------------------------------------


def test_normalizar_01_serie_constante_no_divide_por_cero():
    resultado = normalizar_01(pd.Series([5.0, 5.0, 5.0]))
    assert (resultado == 0).all()


def test_score_prioridad_entre_0_y_100(pipeline_real):
    base_con_score, _, _ = pipeline_real
    assert base_con_score["SCORE_PRIORIDAD"].between(0, 100).all()
    assert base_con_score["SKU"].nunique() == 100


def test_pesos_que_no_suman_uno_lanzan_error(pipeline_real):
    base_con_score, _, _ = pipeline_real
    pesos_invalidos = {"ahorro": 0.5, "rotacion": 0.5, "abc": 0.5, "facilidad_movimiento": 0.0}
    with pytest.raises(ValueError, match="deben sumar 1.0"):
        calcular_score_prioridad(base_con_score, pesos_invalidos, MAPA_ABC_SCORE)


# ---------------------------------------------------------------------
# matriz_sku_zona.py
# ---------------------------------------------------------------------


def test_matriz_tiene_n_sku_por_m_zonas_escenarios(pipeline_real):
    base_con_score, layout_cd, _ = pipeline_real
    matriz = construir_matriz_sku_zona(base_con_score, layout_cd)
    assert len(matriz) == len(base_con_score) * len(layout_cd)
    assert matriz.groupby("SKU")["ES_ZONA_ACTUAL"].sum().eq(1).all()


def test_mejor_zona_teorica_una_fila_por_sku(pipeline_real):
    base_con_score, layout_cd, _ = pipeline_real
    matriz = construir_matriz_sku_zona(base_con_score, layout_cd)
    mejor = mejor_zona_teorica(matriz)
    assert len(mejor) == base_con_score["SKU"].nunique()
    assert "MEJOR_ZONA_TEORICA" in mejor.columns


def test_matriz_invalida_si_zona_actual_no_existe_en_layout():
    base_sintetica = pd.DataFrame(
        {
            "SKU": ["A", "B"],
            "ZONA_ACTUAL": ["ZONA_FANTASMA", "Z1"],
            "N_LINEAS": [10, 5],
            "CARGA_OPERATIVA_MIN": [100, 50],
        }
    )
    layout_sintetico = pd.DataFrame(
        {
            "ZONA": ["Z1"],
            "DISTANCIA_METROS": [10],
            "TIEMPO_MINUTOS": [5],
            "CAPACIDAD_M3_MAX": [100],
        }
    )
    with pytest.raises(MatrizSkuZonaInvalidaError):
        construir_matriz_sku_zona(base_sintetica, layout_sintetico)


# ---------------------------------------------------------------------
# capacidad.py -- confirma el hallazgo ya documentado en CLAUDE_1.md
# punto 4: la restricción de capacidad es vacua en el dataset de práctica.
# ---------------------------------------------------------------------


def test_capacidad_confirma_uso_muy_bajo(pipeline_real):
    _, _, capacidad = pipeline_real
    assert (capacidad["USO_MODELO_ACTUAL_%"] < 5).all()


# ---------------------------------------------------------------------
# optimizador.py
# ---------------------------------------------------------------------


def test_optimizador_asigna_todos_los_sku_y_respeta_tope_movimientos(pipeline_real):
    base_con_score, layout_cd, capacidad = pipeline_real
    resultado = ejecutar_optimizador(base_con_score, layout_cd, capacidad, PORCENTAJE_MAX_MOVIMIENTO)

    assert resultado.estado == "Optimal"
    assert set(resultado.zona_asignada.keys()) == set(base_con_score["SKU"])

    zona_actual = base_con_score.set_index("SKU")["ZONA_ACTUAL"].to_dict()
    n_movidos = sum(1 for sku, zona in resultado.zona_asignada.items() if zona != zona_actual[sku])
    assert n_movidos <= resultado.max_movimientos
    assert resultado.max_movimientos == round(100 * PORCENTAJE_MAX_MOVIMIENTO)


def test_optimizador_infactible_con_capacidad_insuficiente():
    base_sintetica = pd.DataFrame(
        {
            "SKU": ["A", "B"],
            "ZONA_ACTUAL": ["Z1", "Z1"],
            "VOLUMEN_M3": [500.0, 500.0],
            "N_LINEAS": [10, 10],
        }
    )
    layout_sintetico = pd.DataFrame(
        {
            "ZONA": ["Z1"],
            "DISTANCIA_METROS": [10],
            "TIEMPO_MINUTOS": [5],
            "CAPACIDAD_M3_MAX": [100],
        }
    )
    capacidad_sintetica = pd.DataFrame(
        {
            "ZONA": ["Z1"],
            "CAPACIDAD_MAX_M3": [100],
            "VOLUMEN_BASE_NO_MODELADO": [0],
        }
    )
    with pytest.raises(OptimizadorInfactibleError):
        ejecutar_optimizador(
            base_sintetica, layout_sintetico, capacidad_sintetica, porcentaje_max_movimiento=1.0
        )
