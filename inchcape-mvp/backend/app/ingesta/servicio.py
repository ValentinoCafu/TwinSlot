"""Orquestación de `POST /ingesta`: lee el o los archivo(s) fuente
(un Excel con las 6 hojas, o varios CSV sueltos -- uno por tabla), aplica
mapeo y validación, persiste el lote vigente en SQLite y arma el reporte
de filas rechazadas.

Dos orígenes posibles, misma canalización de ahí en adelante
(`_procesar_datasets_crudos`): el dataset de práctica llega como un
único Excel con 6 hojas; un export real de SAP MM/WMS Brainsys es más
probable que llegue como archivos CSV sueltos, uno por tabla -- ninguno
de los dos toca mapeo.py ni validacion.py, ambos comparten la misma
validación y el mismo reporte.
"""

from __future__ import annotations

import io
import re
import unicodedata
from dataclasses import dataclass, field

import pandas as pd
from sqlalchemy import delete, insert

from app.core.db import TABLAS_LOTE, engine, lotes_ingesta
from app.ingesta.mapeo import aplicar_mapeo, hoja_esperada
from app.ingesta.validacion import ResultadoValidacion, validar_integridad_referencial, validar_tabla


class IngestaFatalError(ValueError):
    """Error estructural (hoja/archivo o columna faltante) -- no es una
    fila inválida, es que el origen no corresponde a lo esperado. Aborta
    toda la ingesta del lote, no se persiste nada parcial.
    """


@dataclass
class ReporteIngesta:
    filas_aceptadas: int = 0
    filas_rechazadas: list[dict] = field(default_factory=list)
    resumen_por_tabla: dict[str, dict] = field(default_factory=dict)


def _slug(nombre: str) -> str:
    """Normaliza un nombre de hoja/archivo para emparejar sin depender
    de mayúsculas, tildes, espacios o guiones bajos -- 'PEDIDOS ACTUAL',
    'pedidos_actual' y 'Pedidos-Actual.csv' deben matchear igual."""
    sin_tildes = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", sin_tildes.lower())


def procesar_workbook(contenido: bytes, mapeo: dict) -> ReporteIngesta:
    excel = pd.ExcelFile(io.BytesIO(contenido))

    hojas_faltantes = [
        f"{tabla} (hoja '{hoja_esperada(tabla, mapeo)}')"
        for tabla in TABLAS_LOTE
        if hoja_esperada(tabla, mapeo) not in excel.sheet_names
    ]
    if hojas_faltantes:
        raise IngestaFatalError(
            f"El archivo no contiene todas las hojas requeridas: {hojas_faltantes}. "
            f"Hojas disponibles: {excel.sheet_names}"
        )

    datasets_crudos = {
        tabla: pd.read_excel(excel, sheet_name=hoja_esperada(tabla, mapeo)) for tabla in TABLAS_LOTE
    }
    return _procesar_datasets_crudos(datasets_crudos, mapeo)


def procesar_csvs(archivos: dict[str, bytes], mapeo: dict) -> ReporteIngesta:
    """`archivos`: nombre de archivo (tal como lo mandó el cliente,
    con o sin extensión) -> contenido crudo. Se empareja cada archivo
    con la tabla cuyo `hoja` configurado coincide (ver `_slug`), no por
    orden ni por extensión."""
    indice_por_slug = {_slug(hoja_esperada(tabla, mapeo)): tabla for tabla in TABLAS_LOTE}

    datasets_crudos: dict[str, pd.DataFrame] = {}
    no_reconocidos: list[str] = []
    for nombre, contenido in archivos.items():
        nombre_sin_ext = re.sub(r"\.csv$", "", nombre, flags=re.IGNORECASE)
        tabla = indice_por_slug.get(_slug(nombre_sin_ext))
        if tabla is None:
            no_reconocidos.append(nombre)
            continue
        datasets_crudos[tabla] = pd.read_csv(io.BytesIO(contenido))

    faltantes = [f"{t} (esperado: '{hoja_esperada(t, mapeo)}.csv')" for t in TABLAS_LOTE if t not in datasets_crudos]
    if faltantes or no_reconocidos:
        detalle = []
        if faltantes:
            detalle.append(f"faltan archivos para: {faltantes}")
        if no_reconocidos:
            detalle.append(f"no se reconocieron estos nombres: {no_reconocidos}")
        raise IngestaFatalError(
            "Los CSV enviados no cubren las 6 tablas requeridas -- " + "; ".join(detalle)
        )

    return _procesar_datasets_crudos(datasets_crudos, mapeo)


def _procesar_datasets_crudos(datasets_crudos: dict[str, pd.DataFrame], mapeo: dict) -> ReporteIngesta:
    """Mapeo + validación + integridad referencial + persistencia --
    idéntico sin importar si `datasets_crudos` vino de un Excel con
    varias hojas o de varios CSV sueltos."""
    resultados: dict[str, ResultadoValidacion] = {}
    for tabla in TABLAS_LOTE:
        df_mapeado = aplicar_mapeo(datasets_crudos[tabla], tabla, mapeo)  # puede lanzar ValueError
        resultados[tabla] = validar_tabla(df_mapeado, tabla)

    datasets_validos = {tabla: r.df_valido for tabla, r in resultados.items()}
    problemas_referenciales = validar_integridad_referencial(datasets_validos)

    problemas_por_tabla: dict[str, list[dict]] = {}
    for problema in problemas_referenciales:
        problemas_por_tabla.setdefault(problema["tabla"], []).append(problema)

    for tabla, problemas in problemas_por_tabla.items():
        skus_huerfanos_tabla = {p["datos"]["SKU"] for p in problemas}
        df = datasets_validos[tabla]
        datasets_validos[tabla] = df[~df["SKU"].isin(skus_huerfanos_tabla)].reset_index(drop=True)

    reporte = ReporteIngesta()
    for tabla, resultado in resultados.items():
        filas_ref_de_esta_tabla = problemas_por_tabla.get(tabla, [])
        n_aceptadas = len(datasets_validos[tabla])
        n_rechazadas = resultado.n_rechazadas + len(filas_ref_de_esta_tabla)

        reporte.resumen_por_tabla[tabla] = {"aceptadas": n_aceptadas, "rechazadas": n_rechazadas}
        reporte.filas_aceptadas += n_aceptadas
        for fila in resultado.filas_rechazadas + filas_ref_de_esta_tabla:
            reporte.filas_rechazadas.append(
                {"tabla": tabla, **{k: v for k, v in fila.items() if k != "tabla"}}
            )

    _persistir_lote(datasets_validos)
    _registrar_lote(reporte)
    return reporte


def _persistir_lote(datasets: dict[str, pd.DataFrame]) -> None:
    with engine.begin() as conn:
        for tabla, tabla_sql in TABLAS_LOTE.items():
            conn.execute(delete(tabla_sql))
            df = datasets[tabla]
            if len(df):
                conn.execute(insert(tabla_sql), df.to_dict("records"))


def _registrar_lote(reporte: ReporteIngesta) -> None:
    import json

    with engine.begin() as conn:
        conn.execute(
            insert(lotes_ingesta).values(
                filas_aceptadas=reporte.filas_aceptadas,
                filas_rechazadas=len(reporte.filas_rechazadas),
                resumen_json=json.dumps(reporte.resumen_por_tabla, ensure_ascii=False),
            )
        )
