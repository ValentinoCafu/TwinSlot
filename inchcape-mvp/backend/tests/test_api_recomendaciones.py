from fastapi.testclient import TestClient

from app.main import app


def test_detalle_sku_end_to_end(excel_practica_bytes):
    with TestClient(app) as client:
        client.post(
            "/ingesta", files=[("archivos", ("d.xlsx", excel_practica_bytes, "application/octet-stream"))]
        )
        respuesta = client.get("/recomendaciones/SKU00004")

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()

    assert cuerpo["recomendacion"]["SKU"] == "SKU00004"
    assert cuerpo["desglose_score"]["total"] == cuerpo["recomendacion"]["SCORE_PRIORIDAD"]

    desglose = cuerpo["desglose_score"]
    suma_partes = (
        desglose["ahorro"] + desglose["rotacion"] + desglose["abc"] + desglose["facilidad_movimiento"]
    )
    assert abs(suma_partes - desglose["total"]) < 1e-6

    assert 0 <= cuerpo["explicacion_cluster"]["cluster"] < 10
    assert isinstance(cuerpo["explicacion_cluster"]["contribucion_por_variable"], dict)


def test_detalle_sku_inexistente_404(excel_practica_bytes):
    with TestClient(app) as client:
        client.post(
            "/ingesta", files=[("archivos", ("d.xlsx", excel_practica_bytes, "application/octet-stream"))]
        )
        respuesta = client.get("/recomendaciones/SKU-NO-EXISTE")
    assert respuesta.status_code == 404
