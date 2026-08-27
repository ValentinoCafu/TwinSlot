/** Capacidad y FORMA real de espacios por zona -- respeta el layout que
 * el usuario diseñó en Excel (filas de bloques, cada bloque con un
 * número fijo de columnas por subfila, incluidos los bloques
 * escalonados que siguen el borde diagonal de la zona real).
 *
 * Origen del dato: diseño manual del usuario en Excel, escaneado y
 * confirmado celda a celda (ago 2026). Es una decisión consciente, no
 * un descuido: existe también un número OFICIAL de ubicaciones para 4
 * de estas zonas (Multinivel Cluster=10,636, Multinivel Estantería=1,628,
 * Rack Doble=265, Rack Simple=2,468 -- ver
 * `data/CD_Aldeas_IMPULSA_2026.pdf` p.12, "Mapa de Zonificación por
 * Técnica de Almacenamiento"), pero se optó explícitamente por usar la
 * capacidad ilustrativa del diagrama en vez de la real, para mantener
 * la escala visual manejable en pantalla. Cada celda de esta grilla
 * representa una posición lógica, no 1 ubicación física exacta de SAP/WMS.
 *
 * Cardinalidad: 1 posición = 1 SKU (decisión explícita; el modelo
 * Bin/Quant de un WMS real queda como evolución futura).
 */

/** Un bloque = un rack/isla. Cada número del array es el ancho
 * (columnas) de una subfila interna del bloque -- casi siempre iguales
 * (rectangular), salvo los bloques escalonados que siguen un borde
 * diagonal (ancho decreciente subfila a subfila). */
export type Bloque = number[];
export type FilaEspacios = { bloques: Bloque[] } | { pasillo: true };

export const ESPACIOS_ZONA: Record<string, FilaEspacios[]> = {
  bulk: [
    { bloques: [[5, 5, 5, 5], [5, 5, 5, 5], [5, 5, 5, 5], [8, 8, 7, 7]] },
    { pasillo: true },
    { bloques: [[5, 5, 5, 5], [5, 5, 5, 5], [6, 6, 6, 6]] },
  ],
  neumaticos: [{ bloques: [[13, 13, 13], [11, 11, 11]] }],
  balda22: [
    { bloques: Array.from({ length: 9 }, () => [2, 2, 2]) },
    { bloques: Array.from({ length: 9 }, () => [2, 2, 2]) },
    { bloques: Array.from({ length: 9 }, () => [2, 2, 2]) },
  ],
  balda14: [
    { bloques: Array.from({ length: 8 }, () => [2, 2]) },
    { bloques: Array.from({ length: 8 }, () => [2, 2]) },
    { bloques: Array.from({ length: 8 }, () => [2, 2]) },
  ],
  simple: [
    { bloques: Array.from({ length: 7 }, () => [2, 2]) },
    { bloques: Array.from({ length: 7 }, () => [2, 2]) },
    { bloques: Array.from({ length: 7 }, () => [2, 2]) },
  ],
  doble: [{ bloques: [[50]] }],
  cluster: [
    { bloques: [[5], [11]] },
    { bloques: [[5], [11]] },
  ],
  estanteria: [
    { bloques: [[5, 5], [2, 3]] },
    { bloques: [[5, 5], [3, 4]] },
    { bloques: [[5, 5], [5, 6]] },
    { bloques: [[5, 5], [6, 6]] },
    { bloques: [[5, 5], [7, 7]] },
    { bloques: [[5, 5], [8, 8]] },
    { bloques: [[5, 5], [9, 9]] },
    { bloques: [[5, 5], [10, 10]] },
    { bloques: [[3, 3], [11, 11]] },
  ],
};

function sumaBloque(bloque: Bloque): number {
  return bloque.reduce((a, b) => a + b, 0);
}

export function capacidadTotal(filas: FilaEspacios[]): number {
  return filas.reduce((acc, f) => ('pasillo' in f ? acc : acc + f.bloques.reduce((a, b) => a + sumaBloque(b), 0)), 0);
}

export type SlotEspacio<T> = { ocupado: true; item: T } | { ocupado: false };
/** Un bloque renderizado: un array por subfila interna, cada una con
 * sus slots en el ancho exacto definido -- para que el render pueda
 * usar `grid-template-columns` fijo en vez de auto-ajuste. */
export type BloqueRenderizado<T> = SlotEspacio<T>[][];
export type FilaRenderizadaEspacios<T> = { pasillo: true } | { bloques: BloqueRenderizado<T>[] };

/** Reparte `items` (los SKU reales de la zona) dentro de la capacidad
 * fija de la plantilla, en el orden en que llegan, respetando el ancho
 * exacto de cada subfila. Las posiciones que sobran quedan
 * `ocupado: false` (libres). Si `items` excede la capacidad, el
 * sobrante se reporta en `desbordados` -- nunca se descarta en silencio. */
export function distribuirEnEspacios<T>(
  items: T[],
  filas: FilaEspacios[],
): { filas: FilaRenderizadaEspacios<T>[]; ocupados: number; libres: number; desbordados: number } {
  let cursor = 0;
  const renderizadas = filas.map((fila) => {
    if ('pasillo' in fila) return { pasillo: true as const };
    const bloques = fila.bloques.map((bloque) =>
      bloque.map((ancho) => {
        const subfila: SlotEspacio<T>[] = [];
        for (let i = 0; i < ancho; i++) {
          if (cursor < items.length) {
            subfila.push({ ocupado: true, item: items[cursor] });
            cursor++;
          } else {
            subfila.push({ ocupado: false });
          }
        }
        return subfila;
      }),
    );
    return { bloques };
  });
  const total = capacidadTotal(filas);
  const ocupados = Math.min(items.length, total);
  return { filas: renderizadas, ocupados, libres: total - ocupados, desbordados: Math.max(0, items.length - total) };
}
