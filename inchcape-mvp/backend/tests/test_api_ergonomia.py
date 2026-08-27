from fastapi.testclient import TestClient

from app.main import app


def test_get_ergonomia_end_to_end(excel_practica_bytes):
    with TestClient(app) as client:
        client.post(
            "/ingesta", files=[("archivos", ("d.xlsx", excel_practica_bytes, "application/octet-stream"))]
        )
        respuesta = client.get("/ergonomia")

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["constante_niosh_kg"] == 23.0
    assert cuerpo["rwl_favorable_kg"] == 21.3
    assert cuerpo["rwl_conservador_kg"] == 11.4
    assert len(cuerpo["skus"]) == 100
    assert sum(s["EXCEDE_CONSTANTE_NIOSH"] for s in cuerpo["skus"]) == 53
