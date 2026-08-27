"""Fase 13 del notebook original -- KPI globales del escenario optimizado."""

from __future__ import annotations

import pandas as pd


def calcular_kpis(recomendaciones: pd.DataFrame, max_movimientos: int, n_pedidos: int) -> dict:
    tiempo_total_actual = float(recomendaciones["COSTO_ACTUAL_MIN"].sum())
    tiempo_total_nuevo = float(recomendaciones["COSTO_NUEVO_MIN"].sum())
    ahorro_total = tiempo_total_actual - tiempo_total_nuevo
    ahorro_porcentaje = 100 * ahorro_total / tiempo_total_actual if tiempo_total_actual > 0 else 0

    cantidad_movimientos = int(recomendaciones["MOVIMIENTO"].eq("MOVER").sum())
    porcentaje_movimientos = 100 * cantidad_movimientos / len(recomendaciones)

    # Productividad = líneas completadas / horas-hombre (Σtiempo en horas).
    # Misma fórmula ya verificada contra PEDIDOS ACTUAL en FEATURES-Y-KPIS.md §3.
    n_lineas = float(recomendaciones["N_LINEAS"].sum())
    productividad_actual = n_lineas / (tiempo_total_actual / 60) if tiempo_total_actual > 0 else 0
    productividad_optimizada = n_lineas / (tiempo_total_nuevo / 60) if tiempo_total_nuevo > 0 else 0

    # Tiempo promedio = Σtiempo / n_pedidos (no n_líneas -- ver FEATURES-Y-KPIS.md §2, el
    # error de método más frecuente es dividir entre líneas en vez de entre pedidos).
    tiempo_promedio_actual = tiempo_total_actual / n_pedidos if n_pedidos > 0 else 0
    tiempo_promedio_optimizado = tiempo_total_nuevo / n_pedidos if n_pedidos > 0 else 0

    return {
        "sku_analizados": len(recomendaciones),
        "sku_movidos": cantidad_movimientos,
        "porcentaje_sku_movidos": porcentaje_movimientos,
        "max_movimientos_permitidos": max_movimientos,
        "tiempo_actual_min": tiempo_total_actual,
        "tiempo_optimizado_min": tiempo_total_nuevo,
        "ahorro_min": ahorro_total,
        "reduccion_porcentaje": ahorro_porcentaje,
        "productividad_actual_lineas_hh": productividad_actual,
        "productividad_optimizada_lineas_hh": productividad_optimizada,
        "tiempo_promedio_actual_min_pedido": tiempo_promedio_actual,
        "tiempo_promedio_optimizado_min_pedido": tiempo_promedio_optimizado,
    }
