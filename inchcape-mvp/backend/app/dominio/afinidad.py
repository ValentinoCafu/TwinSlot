"""Motor de afinidad -- Bloque E de `propuesta-scoring-reslotting-6-meses.md`.

No es un puerto del notebook (Valentino no construyó esto); es la
mecánica descrita en `Informacion de Otro Chat/sintesis-arquitectura-mvp-presentacion.md`
§2: el pipeline se ejecuta siempre, pero el propio sistema decide -- con
un test de significancia, no con una opinión -- si hay señal real antes
de dejarlo influir en el score:

    if modularidad_observada <= percentil_95_nulo:
        usar_afinidad = False

Nulo de referencia: permutar la columna SKU de las líneas de pedido
(conserva el tamaño de cada pedido y la popularidad marginal de cada
SKU, solo destruye qué SKU concretos coincidieron) y recalcular la
modularidad `n_replicas` veces -- así el umbral de comparación no es un
número inventado, sale de la misma estructura del dataset.
"""

from __future__ import annotations

import itertools
from collections import Counter
from dataclasses import dataclass

import community as community_louvain
import networkx as nx
import numpy as np
import pandas as pd
from mlxtend.frequent_patterns import fpgrowth
from mlxtend.preprocessing import TransactionEncoder


def construir_pares_coocurrencia(pedidos: pd.DataFrame) -> pd.DataFrame:
    """Lift y Jaccard por par de SKU que aparecieron en el mismo pedido."""
    n_pedidos = pedidos["PEDIDO_ID"].nunique()
    conteo_par: Counter = Counter()
    conteo_sku: Counter = Counter()

    for _, grupo in pedidos.groupby("PEDIDO_ID"):
        skus = sorted(set(grupo["SKU"]))
        for sku in skus:
            conteo_sku[sku] += 1
        for a, b in itertools.combinations(skus, 2):
            conteo_par[(a, b)] += 1

    filas = []
    for (a, b), nij in conteo_par.items():
        na, nb = conteo_sku[a], conteo_sku[b]
        esperado = na * nb / n_pedidos
        filas.append(
            {
                "SKU_A": a,
                "SKU_B": b,
                "N_COOCURRENCIA": nij,
                "SOPORTE": nij / n_pedidos,
                "LIFT": nij / esperado if esperado > 0 else np.nan,
                "JACCARD": nij / (na + nb - nij),
            }
        )
    return pd.DataFrame(filas).sort_values("N_COOCURRENCIA", ascending=False).reset_index(drop=True)


def _grafo_desde_pares(pares: pd.DataFrame) -> nx.Graph:
    G = nx.Graph()
    for _, fila in pares.iterrows():
        G.add_edge(fila["SKU_A"], fila["SKU_B"], weight=fila["N_COOCURRENCIA"])
    return G


def _modularidad(pedidos: pd.DataFrame, seed: int) -> float:
    G = _grafo_desde_pares(construir_pares_coocurrencia(pedidos))
    if G.number_of_edges() == 0:
        return 0.0
    particion = community_louvain.best_partition(G, weight="weight", random_state=seed)
    return community_louvain.modularity(particion, G, weight="weight")


@dataclass
class TestSignificancia:
    modularidad_observada: float
    media_nula: float
    percentil_95_nulo: float
    n_replicas: int
    usar_afinidad: bool


def calcular_significancia_afinidad(
    pedidos: pd.DataFrame, n_replicas: int = 200, seed: int = 42
) -> TestSignificancia:
    modularidad_observada = _modularidad(pedidos, seed)

    rng = np.random.default_rng(seed)
    valores_sku = pedidos["SKU"].to_numpy()
    modularidades_nulas = []
    for _ in range(n_replicas):
        permutado = pedidos.copy()
        permutado["SKU"] = rng.permutation(valores_sku)
        modularidades_nulas.append(_modularidad(permutado, seed))

    percentil_95_nulo = float(np.percentile(modularidades_nulas, 95))
    return TestSignificancia(
        modularidad_observada=modularidad_observada,
        media_nula=float(np.mean(modularidades_nulas)),
        percentil_95_nulo=percentil_95_nulo,
        n_replicas=n_replicas,
        usar_afinidad=modularidad_observada > percentil_95_nulo,
    )


def conjuntos_frecuentes(pedidos: pd.DataFrame, min_items: int = 3) -> pd.DataFrame:
    """Apriori/FP-Growth (Bloque E): combos de N>=3 SKU que aparecen
    juntos con frecuencia -- soporte mínimo bajo a propósito (2 pedidos)
    porque con 435 pedidos y 3.45 líneas/pedido en promedio, un umbral
    convencional (ej. 1%) dejaría la tabla vacía por diseño del dataset,
    no por un bug.
    """
    transacciones = pedidos.groupby("PEDIDO_ID")["SKU"].apply(list).tolist()
    n_pedidos = len(transacciones)
    min_soporte = max(2 / n_pedidos, 1e-6)

    te = TransactionEncoder()
    df_onehot = pd.DataFrame(te.fit(transacciones).transform(transacciones), columns=te.columns_)

    itemsets = fpgrowth(df_onehot, min_support=min_soporte, use_colnames=True)
    if itemsets.empty:
        return pd.DataFrame(columns=["ITEMSET", "N_ITEMS", "FRECUENCIA", "SOPORTE"])

    itemsets["N_ITEMS"] = itemsets["itemsets"].apply(len)
    itemsets = itemsets[itemsets["N_ITEMS"] >= min_items].copy()
    if itemsets.empty:
        return pd.DataFrame(columns=["ITEMSET", "N_ITEMS", "FRECUENCIA", "SOPORTE"])

    itemsets["FRECUENCIA"] = (itemsets["support"] * n_pedidos).round().astype(int)
    itemsets["ITEMSET"] = itemsets["itemsets"].apply(lambda s: " + ".join(sorted(s)))
    return (
        itemsets[["ITEMSET", "N_ITEMS", "FRECUENCIA", "support"]]
        .rename(columns={"support": "SOPORTE"})
        .sort_values("FRECUENCIA", ascending=False)
        .reset_index(drop=True)
    )
