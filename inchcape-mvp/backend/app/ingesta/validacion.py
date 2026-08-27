"""Capa de validación -- rechaza y reporta filas inválidas.

Principio de la sombra digital (`Informacion de Otro Chat/sintesis-...md`
§1): datos sucios se rechazan y se reportan, nunca se descartan en
silencio ni se rellenan con un valor inventado.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

# tabla_canonica -> especificación de validación
ESPECIFICACION_TABLAS: dict[str, dict] = {
    "sku_maestro": {"clave": "SKU", "numericas": ["VOLUMEN_M3", "PESO_KG"]},
    "rotacion": {"clave": "SKU", "numericas": ["ROTACION_6M"]},
    "stock_actual": {"clave": "SKU", "numericas": []},
    "layout_cd": {"clave": "ZONA", "numericas": ["DISTANCIA_METROS", "TIEMPO_MINUTOS", "CAPACIDAD_M3_MAX"]},
    "ocupacion_zona": {
        "clave": "ZONA",
        "numericas": ["CAPACIDAD_MAX_M3", "VOLUMEN_USADO_M3", "VOLUMEN_DISPONIBLE_M3", "PORCENTAJE_USO"],
    },
    "pedidos": {"clave": "SKU", "numericas": ["CANTIDAD", "TIEMPO_HOY_MIN"]},
}


@dataclass
class ResultadoValidacion:
    tabla: str
    df_valido: pd.DataFrame
    filas_rechazadas: list[dict] = field(default_factory=list)

    @property
    def n_aceptadas(self) -> int:
        return len(self.df_valido)

    @property
    def n_rechazadas(self) -> int:
        return len(self.filas_rechazadas)


def validar_tabla(df: pd.DataFrame, tabla: str) -> ResultadoValidacion:
    """Valida clave no nula y tipos numéricos coercibles. Devuelve el
    subconjunto válido y el detalle de cada fila rechazada con su motivo.
    """
    espec = ESPECIFICACION_TABLAS[tabla]
    df = df.reset_index(drop=True).copy()
    motivos: dict[int, list[str]] = {}

    clave = espec["clave"]
    if clave:
        nulos_clave = df[clave].isna() | (df[clave].astype(str).str.strip() == "")
        for i in df.index[nulos_clave]:
            motivos.setdefault(i, []).append(f"'{clave}' vacío")

    for col in espec["numericas"]:
        convertido = pd.to_numeric(df[col], errors="coerce")
        invalido = convertido.isna() & df[col].notna()
        for i in df.index[invalido]:
            motivos.setdefault(i, []).append(f"'{col}' no es numérico (valor: {df.at[i, col]!r})")
        df[col] = convertido

    indices_rechazados = sorted(motivos.keys())
    filas_rechazadas = [
        {"fila": int(i) + 2, "motivo": "; ".join(motivos[i]), "datos": df.loc[i].to_dict()}
        for i in indices_rechazados
    ]  # +2: fila 1 es encabezado y pandas es 0-index -> coincide con el número de fila visible en Excel

    df_valido = df.drop(index=indices_rechazados).reset_index(drop=True)
    return ResultadoValidacion(tabla=tabla, df_valido=df_valido, filas_rechazadas=filas_rechazadas)


def validar_integridad_referencial(
    datasets: dict[str, pd.DataFrame],
) -> list[dict]:
    """SKU en pedidos o stock que no existen en el maestro -- error de
    integridad entre archivos, no de una fila aislada.
    """
    problemas: list[dict] = []
    skus_maestro = set(datasets["sku_maestro"]["SKU"])

    for tabla in ("pedidos", "stock_actual"):
        df = datasets[tabla]
        huerfanos = df[~df["SKU"].isin(skus_maestro)]
        for i, fila in huerfanos.iterrows():
            problemas.append(
                {
                    "tabla": tabla,
                    "fila": int(i) + 2,
                    "motivo": f"SKU '{fila['SKU']}' no existe en sku_maestro",
                    "datos": fila.to_dict(),
                }
            )
    return problemas
