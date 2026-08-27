"""Pruebas de la capa de ingesta contra el Excel de práctica real.

Valores esperados verificados por fuera del código (no adivinados):
100 SKU, 9 zonas de LAYOUT_CD, 1500 líneas de pedido, 435 pedidos únicos,
sin SKU huérfanos ni nulos en el dataset de práctica.
"""

import pytest
from sqlalchemy import select

from app.core.db import engine, sku_maestro
from app.core.db import pedidos as tbl_pedidos
from app.ingesta.mapeo import cargar_config_mapeo
from app.ingesta.servicio import procesar_csvs, procesar_workbook


def test_procesar_workbook_acepta_el_dataset_de_practica_completo(excel_practica_bytes):
    mapeo = cargar_config_mapeo()
    reporte = procesar_workbook(excel_practica_bytes, mapeo)

    assert reporte.filas_rechazadas == []
    # 100 (maestro) + 100 (rotacion) + 100 (stock) + 9 (layout) + 9 (ocupacion) + 1500 (pedidos)
    assert reporte.filas_aceptadas == 100 + 100 + 100 + 9 + 9 + 1500
    assert reporte.resumen_por_tabla["sku_maestro"] == {"aceptadas": 100, "rechazadas": 0}
    assert reporte.resumen_por_tabla["pedidos"] == {"aceptadas": 1500, "rechazadas": 0}
    assert reporte.resumen_por_tabla["layout_cd"] == {"aceptadas": 9, "rechazadas": 0}


def test_procesar_workbook_persiste_en_sqlite(excel_practica_bytes):
    mapeo = cargar_config_mapeo()
    procesar_workbook(excel_practica_bytes, mapeo)

    with engine.connect() as conn:
        n_sku = len(conn.execute(select(sku_maestro)).fetchall())
        n_pedidos = len(conn.execute(select(tbl_pedidos)).fetchall())

    assert n_sku == 100
    assert n_pedidos == 1500


def test_procesar_workbook_rechaza_archivo_sin_hoja_requerida():
    import io

    import pandas as pd

    from app.ingesta.servicio import IngestaFatalError

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame({"SKU": ["A"]}).to_excel(writer, sheet_name="MAESTRO_SKUs", index=False)
    buf.seek(0)

    mapeo = cargar_config_mapeo()
    try:
        procesar_workbook(buf.read(), mapeo)
        pytest.fail("Debió lanzar IngestaFatalError por hojas faltantes")
    except IngestaFatalError as e:
        assert "ROTACIÓN" in str(e) or "ROTACION" in str(e) or "rotacion" in str(e)


def test_procesar_csvs_acepta_el_dataset_de_practica_completo(csvs_practica_por_tabla):
    mapeo = cargar_config_mapeo()
    reporte = procesar_csvs(csvs_practica_por_tabla, mapeo)

    assert reporte.filas_rechazadas == []
    assert reporte.filas_aceptadas == 100 + 100 + 100 + 9 + 9 + 1500
    assert reporte.resumen_por_tabla["pedidos"] == {"aceptadas": 1500, "rechazadas": 0}


def test_procesar_csvs_empareja_nombres_sin_importar_mayusculas_tildes_o_separador(csvs_practica_por_tabla):
    """'ROTACIÓN.csv' debe emparejar igual si el archivo real se llama
    'rotacion.csv' o 'Rotacion-2026.csv' no debería (ver slug exacto vs.
    variantes) -- aquí solo variamos may/tildes/separador manteniendo el
    nombre base, que es el caso real esperado (exports con guiones bajos
    en vez de espacios, sin tildes)."""
    from app.ingesta.servicio import procesar_csvs

    variantes = {
        nombre.replace(" ", "_").replace("Ó", "O").lower(): contenido
        for nombre, contenido in csvs_practica_por_tabla.items()
    }
    mapeo = cargar_config_mapeo()
    reporte = procesar_csvs(variantes, mapeo)
    assert reporte.filas_aceptadas == 100 + 100 + 100 + 9 + 9 + 1500


def test_procesar_csvs_rechaza_si_falta_una_tabla(csvs_practica_por_tabla):
    from app.ingesta.servicio import IngestaFatalError

    incompleto = dict(csvs_practica_por_tabla)
    incompleto.pop("PEDIDOS ACTUAL.csv")

    mapeo = cargar_config_mapeo()
    try:
        procesar_csvs(incompleto, mapeo)
        pytest.fail("Debió lanzar IngestaFatalError por falta la tabla de pedidos")
    except IngestaFatalError as e:
        assert "pedidos" in str(e).lower()
