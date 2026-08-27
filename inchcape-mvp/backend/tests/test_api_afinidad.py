from fastapi.testclient import TestClient

from app.main import app


def test_get_afinidad_end_to_end(excel_practica_bytes):
    """Usa las 200 réplicas por defecto del endpoint -- es la prueba más
    lenta de la suite (~10-15s), a propósito: es el mismo protocolo que
    se muestra en la demo, no una versión recortada."""
    with TestClient(app) as client:
        client.post(
            "/ingesta", files=[("archivos", ("d.xlsx", excel_practica_bytes, "application/octet-stream"))]
        )
        respuesta = client.get("/afinidad")

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()

    assert cuerpo["activo"] is False  # hallazgo ya validado: sin señal con esta muestra
    assert cuerpo["test_significancia"]["n_replicas"] == 200
    assert len(cuerpo["motivo"]) > 0
    assert all(p["N_COOCURRENCIA"] >= 1 for p in cuerpo["pares"])
