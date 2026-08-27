import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.dominio.pipeline import SinLoteIngeridoError, ejecutar_pipeline
from app.main import app


def test_pipeline_sin_lote_ingerido_lanza_error_claro():
    datasets_vacios = {
        nombre: pd.DataFrame()
        for nombre in ("sku_maestro", "rotacion", "stock_actual", "layout_cd", "ocupacion_zona", "pedidos")
    }
    with pytest.raises(SinLoteIngeridoError):
        ejecutar_pipeline(datasets_vacios)


def test_pipeline_end_to_end(excel_practica_bytes):
    with TestClient(app) as client:
        client.post(
            "/ingesta",
            files=[("archivos", ("dataset.xlsx", excel_practica_bytes, "application/octet-stream"))],
        )
        respuesta = client.post("/pipeline/ejecutar")

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()

    assert len(cuerpo["recomendaciones"]) == 100
    assert cuerpo["kpis"]["sku_analizados"] == 100
    assert cuerpo["kpis"]["sku_movidos"] <= cuerpo["kpis"]["max_movimientos_permitidos"]
    # el óptimo nunca puede ser peor que mantener todo igual (esa asignación
    # siempre es factible, así que el solver como mínimo la iguala)
    assert cuerpo["kpis"]["ahorro_min"] >= -1e-6

    primera = cuerpo["recomendaciones"][0]
    assert primera["MOVIMIENTO"] in ("MOVER", "MANTENER")
    assert "JUSTIFICACION" in primera


def test_pipeline_respeta_pesos_score_personalizados(excel_practica_bytes):
    with TestClient(app) as client:
        client.post(
            "/ingesta",
            files=[("archivos", ("dataset.xlsx", excel_practica_bytes, "application/octet-stream"))],
        )
        respuesta = client.post(
            "/pipeline/ejecutar",
            json={"pesos_score": {"ahorro": 1.0, "rotacion": 0, "abc": 0, "facilidad_movimiento": 0}},
        )
    assert respuesta.status_code == 200, respuesta.text


def test_una_regla_de_atributo_cambia_el_resultado_del_optimizador(excel_practica_bytes):
    """Prueba de fuego del motor de reglas: sin la regla, el optimizador
    es libre de mover SKU00004 a donde le convenga; con la regla activa,
    tiene que terminar exactamente en '2. PISO' -- si esto pasa, las
    reglas duras realmente están restringiendo el optimizador, no son
    solo CRUD decorativo.
    """
    regla_id = "R-INTEGRACION-1"
    payload = {
        "id": regla_id,
        "tipo": "atributo",
        "nombre": "Forzar SKU00004 a Bulk (prueba de integración)",
        "definicion": {"campo": "SKU", "operador": "==", "valor": "SKU00004", "zona_permitida": "2. PISO"},
        "activa": True,
        "justificacion": "prueba",
    }

    with TestClient(app) as client:
        client.post(
            "/ingesta",
            files=[("archivos", ("dataset.xlsx", excel_practica_bytes, "application/octet-stream"))],
        )
        client.delete(f"/reglas/{regla_id}")
        client.post("/reglas", json=payload)

        respuesta = client.post("/pipeline/ejecutar")
        assert respuesta.status_code == 200, respuesta.text
        cuerpo = respuesta.json()

        client.delete(f"/reglas/{regla_id}")

    sku0004 = next(r for r in cuerpo["recomendaciones"] if r["SKU"] == "SKU00004")
    assert sku0004["ZONA_RECOMENDADA"] == "2. PISO"

    decision = next(d for d in cuerpo["camino_decision_reglas"] if d["sku"] == "SKU00004")
    assert decision["regla_id"] == regla_id

    assert cuerpo["banderas_activas"]["usar_incompatibilidad_geometrica"] is False
