"""Pruebas de dominio/indicadores.py y dominio/impacto.py (Fases 3-6 del
notebook) contra el dataset de práctica ya persistido en SQLite.
"""

import pandas as pd
import pytest

from app.core.config import PORCENTAJE_TOP_INICIAL
from app.core.db import engine
from app.dominio.impacto import (
    analisis_abc,
    calcular_impacto_operativo,
    construir_base_maestra,
    distribucion_top_abc,
    identificar_top_sku,
    ranking_preliminar,
)
from app.dominio.indicadores import construir_pedidos_por_sku
from app.ingesta.mapeo import cargar_config_mapeo
from app.ingesta.servicio import procesar_workbook


@pytest.fixture(scope="module")
def base_maestra_con_impacto(excel_practica_bytes):
    procesar_workbook(excel_practica_bytes, cargar_config_mapeo())

    with engine.connect() as conn:
        sku_maestro = pd.read_sql("SELECT * FROM sku_maestro", conn)
        rotacion = pd.read_sql("SELECT * FROM rotacion", conn)
        stock_actual = pd.read_sql("SELECT * FROM stock_actual", conn)
        layout_cd = pd.read_sql("SELECT * FROM layout_cd", conn)
        pedidos = pd.read_sql("SELECT * FROM pedidos", conn)

    pedidos_por_sku = construir_pedidos_por_sku(pedidos)
    base = construir_base_maestra(sku_maestro, rotacion, stock_actual, pedidos_por_sku, layout_cd)
    impacto = calcular_impacto_operativo(base, layout_cd)
    return impacto, layout_cd


def test_pedidos_por_sku_conserva_los_100_sku_y_1500_lineas(excel_practica_bytes):
    with engine.connect() as conn:
        pedidos = pd.read_sql("SELECT * FROM pedidos", conn)
    resultado = construir_pedidos_por_sku(pedidos)

    assert resultado["N_LINEAS"].sum() == 1500
    assert not resultado["SKU"].duplicated().any()


def test_base_maestra_tiene_100_sku_sin_nulos_criticos(base_maestra_con_impacto):
    impacto, _ = base_maestra_con_impacto
    base = impacto.base_maestra

    assert len(base) == 100
    assert base["SKU"].nunique() == 100
    assert base["ZONA_ACTUAL"].notna().all()
    assert base["TIEMPO_LAYOUT_ACTUAL"].notna().all()


def test_ahorro_teorico_nunca_es_negativo(base_maestra_con_impacto):
    impacto, _ = base_maestra_con_impacto
    assert (impacto.base_maestra["AHORRO_TEORICO_MIN"] >= 0).all()


def test_tiempo_minimo_cd_coincide_con_el_minimo_de_layout(base_maestra_con_impacto):
    impacto, layout_cd = base_maestra_con_impacto
    assert impacto.tiempo_minimo_cd == layout_cd["TIEMPO_MINUTOS"].min()


def test_top_sku_usa_porcentaje_dinamico_no_hardcodeado(base_maestra_con_impacto):
    impacto, _ = base_maestra_con_impacto
    ranking = ranking_preliminar(impacto.base_maestra)
    top = identificar_top_sku(ranking, PORCENTAJE_TOP_INICIAL)

    # 20% de 100 SKU -> 20, pero la función no debe tener "20" hardcodeado
    # en ningún punto (principio §4.3 de propuesta-mvp-dos-niveles...md)
    assert len(top) == round(len(impacto.base_maestra) * PORCENTAJE_TOP_INICIAL)
    assert (top["CANDIDATO_INICIAL"] == "SÍ").all()


def test_top_sku_con_catalogo_mas_chico_escala_proporcional(base_maestra_con_impacto):
    impacto, _ = base_maestra_con_impacto
    ranking = ranking_preliminar(impacto.base_maestra)
    subconjunto = ranking.head(37)  # tamaño de catálogo arbitrario, no 100
    top = identificar_top_sku(subconjunto, PORCENTAJE_TOP_INICIAL)
    assert len(top) == round(37 * PORCENTAJE_TOP_INICIAL)


def test_analisis_abc_revela_que_abc_no_explica_todo_el_impacto(base_maestra_con_impacto):
    impacto, _ = base_maestra_con_impacto
    ranking = ranking_preliminar(impacto.base_maestra)
    top = identificar_top_sku(ranking, PORCENTAJE_TOP_INICIAL)

    resumen_abc = analisis_abc(impacto.base_maestra)
    distribucion = distribucion_top_abc(top)

    assert set(resumen_abc["ABC"]) <= {"A", "B", "C"}
    # Hallazgo ya documentado en CLAUDE_1.md punto 5 (χ² ABC vs. zona, p=0.646):
    # si el TOP 20% fuera 100% clase A, sería evidencia de que ABC sí basta;
    # se espera que NO sea el caso.
    assert set(distribucion["ABC"]) != {"A"}
