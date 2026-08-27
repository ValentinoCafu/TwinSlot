"""Confirma en vivo el hallazgo ya documentado en CLAUDE_1.md punto 14:
53/100 SKU superan la constante NIOSH de 23 kg."""

import pandas as pd

from app.core.db import engine
from app.dominio.ergonomia import calcular_ergonomia
from app.ingesta.mapeo import cargar_config_mapeo
from app.ingesta.servicio import procesar_workbook


def test_53_de_100_sku_superan_la_constante_niosh(excel_practica_bytes):
    procesar_workbook(excel_practica_bytes, cargar_config_mapeo())
    with engine.connect() as conn:
        sku_maestro = pd.read_sql("SELECT SKU, PESO_KG FROM sku_maestro", conn)

    resultado = calcular_ergonomia(sku_maestro)
    assert resultado["EXCEDE_CONSTANTE_NIOSH"].sum() == 53


def test_apto_conservador_es_subconjunto_de_apto_favorable():
    base = pd.DataFrame({"SKU": ["A", "B", "C"], "PESO_KG": [5.0, 15.0, 25.0]})
    r = calcular_ergonomia(base)
    aptos_conservador = set(r.loc[r["APTO_BANDA_ORO_CONSERVADOR"], "SKU"])
    aptos_favorable = set(r.loc[r["APTO_BANDA_ORO_FAVORABLE"], "SKU"])
    assert aptos_conservador <= aptos_favorable
