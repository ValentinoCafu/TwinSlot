import { apiFetch } from './config';

// Coincide 1:1 con app/schemas/pipeline.py del backend.
export interface RecomendacionSKU {
  RANKING_SCORE: number;
  SKU: string;
  MARCA: string;
  FAMILIA: string;
  ABC: string;
  ROTACION_6M: number;
  N_PEDIDOS: number;
  N_LINEAS: number;
  CANT_TOTAL: number;
  VOLUMEN_M3: number;
  PESO_KG: number;
  ZONA_ACTUAL: string;
  ZONA_RECOMENDADA: string;
  TIEMPO_LAYOUT_ACTUAL: number;
  TIEMPO_NUEVO_MIN: number;
  COSTO_ACTUAL_MIN: number;
  COSTO_NUEVO_MIN: number;
  AHORRO_ESTIMADO_MIN: number;
  AHORRO_PORCENTAJE: number;
  SCORE_PRIORIDAD: number;
  MOVIMIENTO: 'MOVER' | 'MANTENER';
  JUSTIFICACION: string;
  CLUSTER_ML: number;
  PERFIL_ML: string;
  PRIORIDAD_CLUSTER_RANK: number;
  INDICE_IMPACTO_CLUSTER: number;
}

export interface Kpis {
  sku_analizados: number;
  sku_movidos: number;
  porcentaje_sku_movidos: number;
  max_movimientos_permitidos: number;
  tiempo_actual_min: number;
  tiempo_optimizado_min: number;
  ahorro_min: number;
  reduccion_porcentaje: number;
  productividad_actual_lineas_hh: number;
  productividad_optimizada_lineas_hh: number;
  tiempo_promedio_actual_min_pedido: number;
  tiempo_promedio_optimizado_min_pedido: number;
}

export interface DecisionRegla {
  sku: string;
  regla_id: string;
  motivo: string;
}

export interface MetricasML {
  mejor_k: number;
  silhouette: number;
  interpretacion_silhouette: string;
  variables_usadas: string[];
  perfil_clusters: Record<string, number | string>[];
}

export interface BanderasActivas {
  usar_incompatibilidad_geometrica: boolean;
  usar_triage: boolean;
  usar_payback_real: boolean;
  usar_fifo: boolean;
}

export interface RespuestaPipeline {
  recomendaciones: RecomendacionSKU[];
  kpis: Kpis;
  banderas_activas: BanderasActivas;
  camino_decision_reglas: DecisionRegla[];
  ml: MetricasML;
}

export interface PesosScore {
  ahorro: number;
  rotacion: number;
  abc: number;
  facilidad_movimiento: number;
}

export function ejecutarPipeline(
  pesos_score?: PesosScore,
  porcentaje_max_movimiento?: number,
): Promise<RespuestaPipeline> {
  return apiFetch<RespuestaPipeline>('/pipeline/ejecutar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pesos_score: pesos_score ?? null, porcentaje_max_movimiento: porcentaje_max_movimiento ?? null }),
  });
}
