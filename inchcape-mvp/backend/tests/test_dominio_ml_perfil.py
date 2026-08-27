"""Confirma en vivo (reentrenando, no cargando el .joblib) el hallazgo
ya documentado: K=3 con silhouette moderado (~0.26) sobre el dataset de
práctica -- ver Reporte_MVP_Reslotting_Inchcape_ML.pdf de Valentino."""

import pandas as pd
import pytest

from app.core.config import MAPA_ABC_SCORE, PESOS_SCORE
from app.core.db import engine
from app.dominio.impacto import calcular_impacto_operativo, construir_base_maestra
from app.dominio.indicadores import construir_pedidos_por_sku
from app.dominio.ml_perfil import calcular_ml_perfil, explicar_sku
from app.dominio.scoring import calcular_score_prioridad
from app.ingesta.mapeo import cargar_config_mapeo
from app.ingesta.servicio import procesar_workbook


@pytest.fixture(scope="module")
def resultado_ml(excel_practica_bytes):
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
    base_con_score = calcular_score_prioridad(impacto.base_maestra, PESOS_SCORE, MAPA_ABC_SCORE)
    return calcular_ml_perfil(base_con_score)


def test_mejor_k_coincide_con_el_hallazgo_ya_validado(resultado_ml):
    assert resultado_ml.mejor_k == 3
    assert (
        0.15 <= resultado_ml.silhouette <= 0.40
    )  # "moderado", no clara -- el propio aviso que debe mostrarse


def test_cada_sku_tiene_cluster_y_perfil_asignado(resultado_ml):
    base = resultado_ml.base_con_ml
    assert base["CLUSTER_ML"].notna().all()
    assert set(base["PERFIL_ML"].unique()) <= {"Impacto alto", "Impacto medio", "Impacto bajo"}
    assert len(resultado_ml.perfil_clusters) == resultado_ml.mejor_k


def test_explicar_sku_desglosa_por_variable_y_reporta_ambiguedad(resultado_ml):
    sku = resultado_ml.base_con_ml.iloc[0]["SKU"]
    explicacion = explicar_sku(sku, resultado_ml)

    assert explicacion["cluster"] == resultado_ml.base_con_ml.iloc[0]["CLUSTER_ML"]
    assert set(explicacion["contribucion_por_variable"]) == set(resultado_ml.variables_usadas)
    assert explicacion["distancia_cluster_propio"] <= explicacion["distancia_segundo_mas_cercano"] + 1e-9
    assert isinstance(explicacion["asignacion_ambigua"], bool)
    assert -1.0 <= explicacion["silhouette_individual"] <= 1.0
