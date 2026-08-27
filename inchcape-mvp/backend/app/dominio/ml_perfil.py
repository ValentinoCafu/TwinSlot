"""Fases 18-23 del notebook original -- perfil de SKU vía K-Means, con
explicabilidad completa.

Puerto de `MVP_Reslotting_Inchcape.ipynb` (celdas 132-164), con una
diferencia deliberada: el notebook exporta el modelo entrenado a
`modelo_kmeans_reslotting_inchcape.joblib` y lo trata como un artefacto
fijo; aquí se **reentrena en cada ejecución del pipeline** sobre el lote
vigente -- es la única forma de que el mismo código escale de 100 a
12,000+ SKU sin recalibrar nada a mano (principio de
`propuesta-mvp-dos-niveles-sintetico-vs-real.md` §0).

No es afinidad (ver `afinidad.py`): KMeans agrupa por similitud de
atributos individuales, nunca mira si dos SKU aparecieron juntos en un
pedido (`propuesta-motor-reglas-y-explicabilidad.md` §5.6).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_samples, silhouette_score
from sklearn.preprocessing import StandardScaler

VARIABLES_ML = [
    "ROTACION_6M",
    "N_LINEAS",
    "N_PEDIDOS",
    "CANT_TOTAL",
    "VOLUMEN_M3",
    "PESO_KG",
    "TIEMPO_LAYOUT_ACTUAL",
    "CARGA_OPERATIVA_MIN",
    "AHORRO_TEORICO_MIN",
]
VARIABLES_IMPACTO_CLUSTER = ["CARGA_OPERATIVA_MIN", "AHORRO_TEORICO_MIN", "N_LINEAS", "ROTACION_6M"]


@dataclass
class ResultadoML:
    base_con_ml: (
        pd.DataFrame
    )  # + CLUSTER_ML, DISTANCIA_CENTROIDE, PERFIL_ML, PRIORIDAD_CLUSTER_RANK, INDICE_IMPACTO_CLUSTER
    perfil_clusters: pd.DataFrame
    mejor_k: int
    silhouette: float
    interpretacion_silhouette: str
    variables_usadas: list[str]
    # artefactos del modelo, para la explicabilidad por SKU (GET /recomendaciones/{sku})
    modelo: KMeans
    scaler: StandardScaler
    X_scaled_df: pd.DataFrame
    silhouette_por_sku: dict[str, float]


def _interpretar_silhouette(valor: float) -> str:
    if valor >= 0.50:
        return "Separación de clusters relativamente clara."
    if valor >= 0.25:
        return "Estructura de clusters moderada; requiere validación operativa."
    return "Separación débil; los perfiles deben interpretarse con cautela."


def _etiquetar_perfil(rank: int, total_clusters: int) -> str:
    proporcion = rank / total_clusters
    if proporcion <= 1 / 3:
        return "Impacto alto"
    if proporcion <= 2 / 3:
        return "Impacto medio"
    return "Impacto bajo"


def calcular_ml_perfil(
    base_maestra: pd.DataFrame, k_min: int = 2, k_max: int = 8, seed: int = 42
) -> ResultadoML:
    variables_ml = [
        c for c in VARIABLES_ML if base_maestra[c].nunique(dropna=False) > 1
    ]  # Fase 18.3 -- elimina automáticamente variables sin variación

    X = base_maestra[variables_ml].copy()
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    X_scaled_df = pd.DataFrame(X_scaled, columns=variables_ml, index=base_maestra.index)

    max_k = min(k_max, len(base_maestra) - 1)
    evaluacion_k = []
    for k in range(k_min, max_k + 1):
        modelo_k = KMeans(n_clusters=k, random_state=seed, n_init=20)
        etiquetas_k = modelo_k.fit_predict(X_scaled)
        silueta = silhouette_score(X_scaled, etiquetas_k) if len(np.unique(etiquetas_k)) > 1 else np.nan
        evaluacion_k.append({"K": k, "INERCIA": modelo_k.inertia_, "SILHOUETTE": silueta})
    evaluacion_k_df = pd.DataFrame(evaluacion_k)
    mejor_k = int(evaluacion_k_df.loc[evaluacion_k_df["SILHOUETTE"].idxmax(), "K"])

    modelo = KMeans(n_clusters=mejor_k, random_state=seed, n_init=20)
    base = base_maestra.copy()
    base["CLUSTER_ML"] = modelo.fit_predict(X_scaled)

    distancias_centroides = modelo.transform(X_scaled)
    base["DISTANCIA_CENTROIDE"] = [distancias_centroides[i, c] for i, c in enumerate(base["CLUSTER_ML"])]

    silhouette_final = float(silhouette_score(X_scaled, base["CLUSTER_ML"]))
    silhouette_muestras = silhouette_samples(X_scaled, base["CLUSTER_ML"])
    silhouette_por_sku = dict(zip(base["SKU"], silhouette_muestras.tolist(), strict=True))

    perfil_clusters = base.groupby("CLUSTER_ML")[variables_ml].mean()
    perfil_clusters["CANTIDAD_SKU"] = base.groupby("CLUSTER_ML").size()
    perfil_clusters = perfil_clusters.reset_index()

    variables_impacto = [v for v in VARIABLES_IMPACTO_CLUSTER if v in variables_ml]
    perfil_impacto = base.groupby("CLUSTER_ML")[variables_impacto].mean().reset_index()
    for col in variables_impacto:
        perfil_impacto[col + "_NORM"] = _normalizar_01(perfil_impacto[col])
    perfil_impacto["INDICE_IMPACTO_CLUSTER"] = perfil_impacto[[c + "_NORM" for c in variables_impacto]].mean(
        axis=1
    )
    perfil_impacto["PRIORIDAD_CLUSTER_RANK"] = (
        perfil_impacto["INDICE_IMPACTO_CLUSTER"].rank(method="dense", ascending=False).astype(int)
    )
    perfil_impacto["PERFIL_ML"] = perfil_impacto["PRIORIDAD_CLUSTER_RANK"].apply(
        lambda r: _etiquetar_perfil(r, mejor_k)
    )

    perfil_clusters_final = (
        perfil_clusters.merge(
            perfil_impacto[["CLUSTER_ML", "INDICE_IMPACTO_CLUSTER", "PRIORIDAD_CLUSTER_RANK", "PERFIL_ML"]],
            on="CLUSTER_ML",
            how="left",
        )
        .sort_values("PRIORIDAD_CLUSTER_RANK")
        .reset_index(drop=True)
    )

    mapa_perfil = perfil_impacto.set_index("CLUSTER_ML")["PERFIL_ML"].to_dict()
    mapa_rank = perfil_impacto.set_index("CLUSTER_ML")["PRIORIDAD_CLUSTER_RANK"].to_dict()
    mapa_indice = perfil_impacto.set_index("CLUSTER_ML")["INDICE_IMPACTO_CLUSTER"].to_dict()
    base["PERFIL_ML"] = base["CLUSTER_ML"].map(mapa_perfil)
    base["PRIORIDAD_CLUSTER_RANK"] = base["CLUSTER_ML"].map(mapa_rank)
    base["INDICE_IMPACTO_CLUSTER"] = base["CLUSTER_ML"].map(mapa_indice)

    return ResultadoML(
        base_con_ml=base,
        perfil_clusters=perfil_clusters_final,
        mejor_k=mejor_k,
        silhouette=silhouette_final,
        interpretacion_silhouette=_interpretar_silhouette(silhouette_final),
        variables_usadas=variables_ml,
        modelo=modelo,
        scaler=scaler,
        X_scaled_df=X_scaled_df,
        silhouette_por_sku=silhouette_por_sku,
    )


def _normalizar_01(serie: pd.Series) -> pd.Series:
    minimo, maximo = serie.min(), serie.max()
    if pd.isna(minimo) or pd.isna(maximo) or maximo == minimo:
        return pd.Series(np.zeros(len(serie)), index=serie.index)
    return (serie - minimo) / (maximo - minimo)


def explicar_sku(sku: str, resultado: ResultadoML) -> dict:
    """Desglose no-caja-negra de la asignación de cluster de un SKU:
    contribución al cuadrado por variable, distancia al centroide propio
    vs. al segundo más cercano, y silhouette individual -- las 4 piezas
    que pide `propuesta-motor-reglas-y-explicabilidad.md` §5.5.
    """
    base = resultado.base_con_ml
    fila = base.loc[base["SKU"] == sku].iloc[0]
    cluster_propio = int(fila["CLUSTER_ML"])

    x_sku = resultado.X_scaled_df.loc[fila.name]
    centroides = resultado.modelo.cluster_centers_
    distancias_a_centroides = np.linalg.norm(centroides - x_sku.to_numpy(), axis=1)

    orden = np.argsort(distancias_a_centroides)
    cluster_mas_cercano = int(orden[0])
    segundo_cluster = int(orden[1]) if len(orden) > 1 else cluster_mas_cercano

    centroide_propio = centroides[cluster_propio]
    contribucion_por_variable = {
        var: float((x_sku[var] - centroide_propio[i]) ** 2)
        for i, var in enumerate(resultado.variables_usadas)
    }

    return {
        "cluster": cluster_propio,
        "perfil": fila["PERFIL_ML"],
        "distancia_cluster_propio": float(distancias_a_centroides[cluster_propio]),
        "distancia_segundo_mas_cercano": float(distancias_a_centroides[segundo_cluster]),
        "asignacion_ambigua": cluster_mas_cercano != cluster_propio,
        "silhouette_individual": float(resultado.silhouette_por_sku[sku]),
        "contribucion_por_variable": contribucion_por_variable,
    }
