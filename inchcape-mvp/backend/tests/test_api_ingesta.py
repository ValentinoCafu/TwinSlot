"""Prueba end-to-end vía HTTP: cliente -> FastAPI -> ingesta -> SQLite."""

from fastapi.testclient import TestClient

from app.main import app


def test_post_ingesta_excel_end_to_end(excel_practica_bytes):
    with TestClient(app) as client:
        respuesta = client.post(
            "/ingesta",
            files=[
                (
                    "archivos",
                    (
                        "IMPULSA_CD_Practico_Estudiantes.xlsx",
                        excel_practica_bytes,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    ),
                )
            ],
        )

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["filas_aceptadas"] == 100 + 100 + 100 + 9 + 9 + 1500
    assert cuerpo["filas_rechazadas"] == []
    assert cuerpo["resumen_por_tabla"]["pedidos"]["aceptadas"] == 1500


def test_post_ingesta_csv_end_to_end(csvs_practica_por_tabla):
    with TestClient(app) as client:
        respuesta = client.post(
            "/ingesta",
            files=[("archivos", (nombre, contenido, "text/csv")) for nombre, contenido in csvs_practica_por_tabla.items()],
        )

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["filas_aceptadas"] == 100 + 100 + 100 + 9 + 9 + 1500
    assert cuerpo["filas_rechazadas"] == []


def test_post_ingesta_csv_incompleto_se_rechaza(csvs_practica_por_tabla):
    incompleto = dict(csvs_practica_por_tabla)
    incompleto.pop("PEDIDOS ACTUAL.csv")
    with TestClient(app) as client:
        respuesta = client.post(
            "/ingesta",
            files=[("archivos", (nombre, contenido, "text/csv")) for nombre, contenido in incompleto.items()],
        )
    assert respuesta.status_code == 422
    assert "pedidos" in respuesta.json()["detail"].lower()


def test_post_ingesta_rechaza_extension_no_soportada():
    with TestClient(app) as client:
        respuesta = client.post(
            "/ingesta",
            files=[("archivos", ("datos.txt", b"algo", "text/plain"))],
        )
    assert respuesta.status_code == 422


def test_salud():
    with TestClient(app) as client:
        respuesta = client.get("/salud")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "ok"}
