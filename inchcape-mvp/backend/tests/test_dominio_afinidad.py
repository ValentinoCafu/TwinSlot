"""Confirma en vivo el hallazgo ya documentado en CLAUDE_1.md punto 3:
sin señal de afinidad entre SKU en el dataset de práctica.

n_replicas bajo aquí (no 200) solo para que la prueba sea rápida -- el
test de significancia real con 200 réplicas se ejerce en
test_api_afinidad.py, que usa el default del endpoint.
"""

import pandas as pd

from app.core.db import engine
from app.dominio.afinidad import (
    calcular_significancia_afinidad,
    conjuntos_frecuentes,
    construir_pares_coocurrencia,
)
from app.ingesta.mapeo import cargar_config_mapeo
from app.ingesta.servicio import procesar_workbook


def test_sin_senal_de_afinidad_en_el_dataset_de_practica(excel_practica_bytes):
    procesar_workbook(excel_practica_bytes, cargar_config_mapeo())
    with engine.connect() as conn:
        pedidos = pd.read_sql("SELECT * FROM pedidos", conn)

    pares = construir_pares_coocurrencia(pedidos)
    assert pares["N_COOCURRENCIA"].max() <= 4  # ya confirmado: Nij máximo = 4

    resultado = calcular_significancia_afinidad(pedidos, n_replicas=20, seed=1)
    assert resultado.usar_afinidad is False


def test_conjuntos_frecuentes_no_falla_con_soporte_bajo(excel_practica_bytes):
    with engine.connect() as conn:
        pedidos = pd.read_sql("SELECT * FROM pedidos", conn)
    itemsets = conjuntos_frecuentes(pedidos)
    assert (itemsets["N_ITEMS"] >= 3).all()
