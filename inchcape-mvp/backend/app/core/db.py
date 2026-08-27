"""Persistencia SQLite -- un archivo, cero configuración.

Esquema completo definido desde el día uno (principio §4.1 de
`propuesta-mvp-dos-niveles-sintetico-vs-real.md`): las tablas de Nivel 2
(`slotting_inicial`, `historico_mensual`, `fecha_alta_sku`,
`incidentes_ergonomicos`) existen aunque hoy lleguen vacías -- el código
que las consumirá se activa solo cuando `core/flags.py` detecte filas en
ellas, sin que el esquema tenga que cambiar.

Se usa SQLAlchemy Core (no el ORM completo): da tipado y `upsert`/`delete`
expresivos sin la sobreingeniería de un ORM para un MVP de 12 días.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    func,
)

from app.core.config import DB_PATH

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)
metadata = MetaData()

# ---------------------------------------------------------------------
# Tablas del lote vigente (se reemplazan por completo en cada POST /ingesta,
# porque la arquitectura es por lotes, no incremental -- ver
# `propuesta-arquitectura-tecnica-react-fastapi.md` §2)
# ---------------------------------------------------------------------

sku_maestro = Table(
    "sku_maestro",
    metadata,
    Column("SKU", String, primary_key=True),
    Column("MARCA", String),
    Column("FAMILIA", String),
    Column("VOLUMEN_M3", Float),
    Column("PESO_KG", Float),
)

rotacion = Table(
    "rotacion",
    metadata,
    Column("SKU", String, primary_key=True),
    Column("ROTACION_6M", Float),
    Column("ABC", String),
)

stock_actual = Table(
    "stock_actual",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("UBICACION", String),
    Column("SKU", String),
    Column("ZONA_ACTUAL", String),
)

layout_cd = Table(
    "layout_cd",
    metadata,
    Column("ZONA", String, primary_key=True),
    Column("DISTANCIA_METROS", Float),
    Column("TIEMPO_MINUTOS", Float),
    Column("CAPACIDAD_M3_MAX", Float),
)

ocupacion_zona = Table(
    "ocupacion_zona",
    metadata,
    Column("ZONA", String, primary_key=True),
    Column("CAPACIDAD_MAX_M3", Float),
    Column("VOLUMEN_USADO_M3", Float),
    Column("VOLUMEN_DISPONIBLE_M3", Float),
    Column("PORCENTAJE_USO", Float),
)

pedidos = Table(
    "pedidos",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("PEDIDO_ID", String),
    Column("LINEA", Integer),
    Column("SKU", String),
    Column("CANTIDAD", Float),
    Column("ZONA_ACTUAL", String),
    Column("TIEMPO_HOY_MIN", Float),
)

# ---------------------------------------------------------------------
# Geometría estática (13 zonas del plano vectorial) -- no depende del
# lote de datos, se siembra una sola vez desde `zonas.json`
# ---------------------------------------------------------------------

zonas = Table(
    "zonas",
    metadata,
    Column("id", String, primary_key=True),
    Column("nombre", String),
    Column("clave_excel", String),
    Column("distancia_m", Float),
    Column("ubicaciones", String),
    Column("lineas_picking", Integer),
    Column("color", String),
    Column("puntos_svg", Text),
    Column("label_x", Float),
    Column("label_y", Float),
    Column("label_fs", Float),
    Column("label_rot", Float),
    Column("texto_claro", Boolean),
)

# ---------------------------------------------------------------------
# Motor de reglas -- CRUD llega en el bloque 4 del cronograma, pero el
# esquema se crea ahora
# ---------------------------------------------------------------------

reglas = Table(
    "reglas",
    metadata,
    Column("id", String, primary_key=True),
    Column("tipo", String, nullable=False),  # atributo | incompatibilidad | umbral
    Column("nombre", String, nullable=False),
    Column(
        "definicion_json", Text, nullable=False
    ),  # payload específico del tipo (ver dominio/reglas/modelos.py)
    Column("activa", Boolean, nullable=False, server_default="1"),
    Column("justificacion", Text),
)

# ---------------------------------------------------------------------
# Resultado del último lote procesado por el pipeline
# ---------------------------------------------------------------------

resultados_ultimo_lote = Table(
    "resultados_ultimo_lote",
    metadata,
    Column("SKU", String, primary_key=True),
    Column("resultado_json", Text, nullable=False),
    Column("fecha_ejecucion", DateTime, server_default=func.now()),
)

lotes_ingesta = Table(
    "lotes_ingesta",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("fecha_carga", DateTime, server_default=func.now()),
    Column("filas_aceptadas", Integer),
    Column("filas_rechazadas", Integer),
    Column("resumen_json", Text),
)

# ---------------------------------------------------------------------
# Tablas de Nivel 2 -- esquema listo, vacías hasta que exista el dato
# real (roadmap detallado en propuesta-mvp-dos-niveles...md §3)
# ---------------------------------------------------------------------

slotting_inicial = Table(
    "slotting_inicial",
    metadata,
    Column("SKU", String, primary_key=True),
    Column("ZONA_ASIGNADA", String),
    Column("FECHA_ASIGNACION", DateTime),
    Column("TIEMPO_TEORICO_ORIGINAL", Float),
)

historico_mensual = Table(
    "historico_mensual",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("SKU", String),
    Column("MES", String),
    Column("HITS", Integer),
)

fecha_alta_sku = Table(
    "fecha_alta_sku",
    metadata,
    Column("SKU", String, primary_key=True),
    Column("FECHA_ALTA", DateTime),
)

incidentes_ergonomicos = Table(
    "incidentes_ergonomicos",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("SKU", String),
    Column("ZONA", String),
    Column("FECHA", DateTime),
    Column("DESCRIPCION", Text),
)


def init_db() -> None:
    """Crea el esquema completo si no existe. Idempotente."""
    metadata.create_all(engine)


def seed_zonas_si_vacio() -> None:
    """Siembra la geometría estática de las 13 zonas (`data/zonas.json`,
    portada de `V1 planta-cd-aldeas-vectorial.html`) una sola vez -- no
    depende del lote de datos ingerido, así que no se reemplaza en cada
    `POST /ingesta` como sí ocurre con `TABLAS_LOTE`.
    """
    import json

    from sqlalchemy import insert, select

    from app.core.config import ZONAS_JSON_PATH

    with engine.begin() as conn:
        ya_sembrado = conn.execute(select(zonas.c.id).limit(1)).first()
        if ya_sembrado:
            return
        datos = json.loads(ZONAS_JSON_PATH.read_text(encoding="utf-8"))
        conn.execute(insert(zonas), datos)


TABLAS_LOTE = {
    "sku_maestro": sku_maestro,
    "rotacion": rotacion,
    "stock_actual": stock_actual,
    "layout_cd": layout_cd,
    "ocupacion_zona": ocupacion_zona,
    "pedidos": pedidos,
}


def leer_tablas_lote() -> dict:
    """El lote vigente (último `POST /ingesta` exitoso), una tabla por
    hoja fuente. Vacío (0 filas) si nunca se ingirió nada.
    """
    import pandas as pd

    with engine.connect() as conn:
        return {nombre: pd.read_sql(f"SELECT * FROM {nombre}", conn) for nombre in TABLAS_LOTE}
