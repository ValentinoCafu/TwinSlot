import { apiFetch } from './config';
import type { DecisionRegla, RecomendacionSKU } from './pipeline';

export interface DesgloseScore {
  ahorro: number;
  rotacion: number;
  abc: number;
  facilidad_movimiento: number;
  total: number;
}

export interface ExplicacionCluster {
  cluster: number;
  perfil: string;
  distancia_cluster_propio: number;
  distancia_segundo_mas_cercano: number;
  asignacion_ambigua: boolean;
  silhouette_individual: number;
  contribucion_por_variable: Record<string, number>;
}

export interface RespuestaRecomendacionSKU {
  recomendacion: RecomendacionSKU;
  desglose_score: DesgloseScore;
  reglas_aplicadas: DecisionRegla[];
  explicacion_cluster: ExplicacionCluster;
}

export function fetchDetalleSku(sku: string): Promise<RespuestaRecomendacionSKU> {
  return apiFetch<RespuestaRecomendacionSKU>(`/recomendaciones/${encodeURIComponent(sku)}`);
}
