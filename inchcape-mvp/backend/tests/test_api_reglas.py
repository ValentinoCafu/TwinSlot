from fastapi.testclient import TestClient

from app.main import app

REGLA_ATRIBUTO = {
    "id": "R-API-1",
    "tipo": "atributo",
    "nombre": "Correas al piso",
    "definicion": {"campo": "FAMILIA", "operador": "==", "valor": "Correas", "zona_permitida": "Bulk"},
    "activa": True,
    "justificacion": "prueba",
}


def test_crud_reglas_via_api():
    with TestClient(app) as client:
        client.delete(f"/reglas/{REGLA_ATRIBUTO['id']}")  # limpia si quedó de una corrida anterior

        creada = client.post("/reglas", json=REGLA_ATRIBUTO)
        assert creada.status_code == 201, creada.text

        duplicada = client.post("/reglas", json=REGLA_ATRIBUTO)
        assert duplicada.status_code == 409

        listado = client.get("/reglas").json()
        assert any(r["id"] == REGLA_ATRIBUTO["id"] for r in listado)

        actualizada = dict(REGLA_ATRIBUTO, nombre="Renombrada")
        r = client.put(f"/reglas/{REGLA_ATRIBUTO['id']}", json=actualizada)
        assert r.status_code == 200
        assert r.json()["nombre"] == "Renombrada"

        eliminada = client.delete(f"/reglas/{REGLA_ATRIBUTO['id']}")
        assert eliminada.status_code == 204

        no_encontrada = client.put(f"/reglas/{REGLA_ATRIBUTO['id']}", json=actualizada)
        assert no_encontrada.status_code == 404


def test_regla_con_definicion_que_no_coincide_con_tipo_devuelve_422():
    payload = dict(REGLA_ATRIBUTO, id="R-API-2", tipo="incompatibilidad")
    with TestClient(app) as client:
        respuesta = client.post("/reglas", json=payload)
    assert respuesta.status_code == 422
