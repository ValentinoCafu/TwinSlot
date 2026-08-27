import os
import tempfile
from pathlib import Path

import pytest

_tmp_dir = tempfile.mkdtemp(prefix="mvp_inchape_test_")
os.environ["MVP_DB_PATH"] = str(Path(_tmp_dir) / "test.db")

EXCEL_PRACTICA = Path(__file__).resolve().parents[3] / "data" / "IMPULSA_CD_Práctico Estudiantes (1).xlsx"


@pytest.fixture(scope="session")
def excel_practica_bytes() -> bytes:
    assert EXCEL_PRACTICA.exists(), f"No se encontró el Excel de práctica en {EXCEL_PRACTICA}"
    return EXCEL_PRACTICA.read_bytes()


@pytest.fixture(scope="session")
def csvs_practica_por_tabla(excel_practica_bytes: bytes) -> dict[str, bytes]:
    """Las mismas 6 hojas del Excel de práctica, cada una convertida a
    CSV -- para probar el modo multi-CSV con datos reales, sin depender
    de un archivo CSV separado en el repo."""
    import io

    import pandas as pd

    from app.ingesta.mapeo import cargar_config_mapeo

    mapeo = cargar_config_mapeo()
    excel = pd.ExcelFile(io.BytesIO(excel_practica_bytes))
    salida: dict[str, bytes] = {}
    for tabla, definicion in mapeo.items():
        df = pd.read_excel(excel, sheet_name=definicion["hoja"])
        salida[f"{definicion['hoja']}.csv"] = df.to_csv(index=False).encode("utf-8")
    return salida
