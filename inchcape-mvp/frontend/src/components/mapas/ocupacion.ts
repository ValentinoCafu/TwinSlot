import type { RecomendacionSKU } from '../../api/pipeline';
import type { Zona } from '../../api/zonas';

/** ZONA_ACTUAL/ZONA_RECOMENDADA usan los 9 nombres de layout_cd (el
 * Excel); las zonas geométricas del plano vectorial son 13 y se
 * relacionan por `clave_excel`, no por nombre -- ver
 * `README.md` backend §3.1 y CLAUDE_1.md #8. */
export function agruparSkusPorZonaExcel(
  recomendaciones: RecomendacionSKU[],
  campo: 'ZONA_ACTUAL' | 'ZONA_RECOMENDADA',
): Map<string, RecomendacionSKU[]> {
  const mapa = new Map<string, RecomendacionSKU[]>();
  for (const r of recomendaciones) {
    const clave = r[campo];
    const lista = mapa.get(clave);
    if (lista) lista.push(r);
    else mapa.set(clave, [r]);
  }
  return mapa;
}

export interface OcupacionZona {
  clave_excel: string;
  count: number;
  skus: string[];
}

export function agruparPorZonaExcel(
  recomendaciones: RecomendacionSKU[],
  campo: 'ZONA_ACTUAL' | 'ZONA_RECOMENDADA',
): Map<string, OcupacionZona> {
  const mapa = new Map<string, OcupacionZona>();
  for (const [clave, skus] of agruparSkusPorZonaExcel(recomendaciones, campo)) {
    mapa.set(clave, { clave_excel: clave, count: skus.length, skus: skus.map((s) => s.SKU) });
  }
  return mapa;
}

/** Dos pares de zonas geométricas comparten el mismo `clave_excel` (ver
 * README backend §3.1): "4. RACK BALDA" -> balda14/balda22, y
 * "8. CLUSTER" -> cluster/clustan. El Excel no trae un campo más
 * granular para distinguir cuál de las dos es -- por decisión explícita
 * del usuario, un SKU genérico se cuenta SIEMPRE en la zona primaria,
 * nunca en ambas (si no fuera así, cualquier vista que agrupe por
 * clave_excel duplicaría el conteo en las dos geometrías). */
const ZONA_PRIMARIA_POR_CLAVE_EXCEL: Record<string, string> = {
  '4. RACK BALDA': 'balda14',
  '8. CLUSTER': 'cluster',
};

export function esZonaPrimariaParaSuClave(zona: Zona): boolean {
  const primaria = ZONA_PRIMARIA_POR_CLAVE_EXCEL[zona.clave_excel];
  return !primaria || primaria === zona.id;
}

/** Zonas del Excel que no tienen un polígono geométrico confirmado en
 * el plano vectorial (ej. "14. LATERALES") -- se reportan explícitamente,
 * nunca se ocultan ni se les inventa una posición. */
export function zonasSinGeometria(ocupacion: Map<string, OcupacionZona>, zonas: Zona[]): OcupacionZona[] {
  const clavesConGeometria = new Set(zonas.map((z) => z.clave_excel));
  return [...ocupacion.values()].filter((o) => !clavesConGeometria.has(o.clave_excel));
}
