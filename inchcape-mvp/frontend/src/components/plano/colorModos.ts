import type { Zona } from '../../api/zonas';

// Misma matemática de color que V1 planta-cd-aldeas-vectorial.html --
// se porta el cálculo, no solo el resultado, para que siga funcionando
// cuando lleguen más zonas reales (nunca "13" hardcodeado).
export type Modo = 'tec' | 'den' | 'dis';

export const ETIQUETA_MODO: Record<Modo, string> = {
  tec: 'Color por técnica de almacenamiento',
  den: 'Color por densidad de picking',
  dis: 'Color por distancia al I/O',
};

function rangoDensidad(zonas: Zona[]) {
  return Math.max(...zonas.map((z) => z.lineas_picking)) || 1;
}

function rangoDistancia(zonas: Zona[]) {
  const distancias = zonas.map((z) => z.distancia_m);
  return { min: Math.min(...distancias), max: Math.max(...distancias) };
}

export function calcularFill(zona: Zona, modo: Modo, zonas: Zona[]): string {
  if (modo === 'tec') return zona.color;

  if (modo === 'den') {
    if (zona.lineas_picking === 0) return '#FFFFFF';
    const hmax = rangoDensidad(zonas);
    const pct = Math.round(14 + (zona.lineas_picking / hmax) * 86);
    return `color-mix(in srgb, #0F5F8F ${pct}%, #DCE6ED)`;
  }

  const { min, max } = rangoDistancia(zonas);
  const t = max === min ? 0 : (zona.distancia_m - min) / (max - min);
  const pct = Math.round(8 + t * 82);
  return `color-mix(in srgb, #BE3A1D ${pct}%, #FFE9C9)`;
}

export function esTextoClaro(zona: Zona, modo: Modo, zonas: Zona[]): boolean {
  if (modo === 'tec') return zona.texto_claro;

  if (modo === 'den') {
    const hmax = rangoDensidad(zonas);
    return zona.lineas_picking / hmax > 0.55;
  }

  const { min, max } = rangoDistancia(zonas);
  const t = max === min ? 0 : (zona.distancia_m - min) / (max - min);
  return t > 0.6;
}
