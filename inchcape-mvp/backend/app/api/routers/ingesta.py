import json

from fastapi import APIRouter, Form, HTTPException, UploadFile

from app.ingesta.mapeo import cargar_config_mapeo
from app.ingesta.servicio import IngestaFatalError, procesar_csvs, procesar_workbook
from app.schemas.ingesta import RespuestaIngesta

router = APIRouter(prefix="/ingesta", tags=["ingesta"])


@router.get("/mapeo")
def obtener_mapeo() -> dict:
    """El mapeo vigente (`data/config_mapeo.yaml` o el default identidad)
    -- lo usa el frontend para precargar la tabla editable antes de
    ingerir un archivo con nombres de columna distintos."""
    return cargar_config_mapeo()


@router.post("", response_model=RespuestaIngesta)
async def ingestar_lote(archivos: list[UploadFile], mapeo: str | None = Form(None)) -> RespuestaIngesta:
    """Recibe el lote fuente en uno de dos formatos y reemplaza el lote
    vigente en SQLite:

    - **Un Excel** (.xlsx/.xls) con las 6 hojas fuente -- el dataset de
      práctica llega así.
    - **Varios CSV**, uno por tabla, emparejados por nombre de archivo
      contra el `hoja` configurado en el mapeo (ver `servicio._slug` --
      no importan mayúsculas/tildes/guiones). Formato más probable para
      un export real de SAP MM/WMS Brainsys.

    Aplica la capa de mapeo configurable (la del servidor, o la que
    envíe el cliente en `mapeo` como JSON) y de validación. Rechaza y
    reporta filas inválidas -- nunca falla en silencio.
    """
    if not archivos:
        raise HTTPException(422, detail="No se recibió ningún archivo.")

    nombres = [a.filename or "" for a in archivos]
    es_excel = len(archivos) == 1 and nombres[0].lower().endswith((".xlsx", ".xls"))
    es_csv = all(n.lower().endswith(".csv") for n in nombres)

    if not es_excel and not es_csv:
        raise HTTPException(
            422,
            detail="Se espera un único archivo Excel (.xlsx/.xls) con las 6 hojas fuente, "
            "o varios archivos .csv (uno por tabla).",
        )

    try:
        mapeo_dict = json.loads(mapeo) if mapeo else cargar_config_mapeo()
    except json.JSONDecodeError as e:
        raise HTTPException(422, detail=f"El mapeo enviado no es JSON válido: {e}") from e

    try:
        if es_excel:
            contenido = await archivos[0].read()
            reporte = procesar_workbook(contenido, mapeo_dict)
        else:
            contenidos = {a.filename or "": await a.read() for a in archivos}
            reporte = procesar_csvs(contenidos, mapeo_dict)
    except IngestaFatalError as e:
        raise HTTPException(422, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(422, detail=str(e)) from e

    return RespuestaIngesta(
        filas_aceptadas=reporte.filas_aceptadas,
        filas_rechazadas=reporte.filas_rechazadas,
        resumen_por_tabla=reporte.resumen_por_tabla,
    )
