/** Plantillas de disposición por zona -- filas de bloques (racks) con
 * pasillos entre ellas, una por cada una de las 13 zonas geométricas.
 *
 * Son ILUSTRATIVAS, no medidas: `STOCK_ACTUAL.UBICACIÓN` es solo un
 * código secuencial (UB00001...), sin fila/columna/nivel real -- no
 * existe el dato para replicar la estantería física exacta. Lo que sí
 * es real es la técnica de almacenamiento de cada zona (`zonas.json` /
 * el plano vectorial), así que la forma de cada plantilla se diseñó
 * para parecerse a esa técnica (multinivel = más filas y más densidad,
 * piso/bulk = bloques grandes con pasillos anchos, colgantes = una
 * fila larga), no a una medición.
 */

export type FilaZona = { bloques: number } | { pasillo: true };

export const PLANTILLAS_ZONA: Record<string, FilaZona[]> = {
  // Multinivel Cluster -- denso, muchos niveles pequeños
  cluster: [{ bloques: 3 }, { bloques: 3 }, { pasillo: true }, { bloques: 3 }, { bloques: 3 }],
  clustan: [{ bloques: 2 }, { bloques: 2 }],
  // Recepción de aéreos -- área de tránsito, poca densidad
  recepcion: [{ bloques: 2 }, { bloques: 2 }],
  // Multinivel Estantería -- el rack más grande del plano
  estanteria: [{ bloques: 4 }, { bloques: 4 }, { bloques: 4 }, { pasillo: true }, { bloques: 4 }, { bloques: 4 }],
  doble: [{ bloques: 3 }, { bloques: 3 }],
  simple: [{ bloques: 3 }, { bloques: 3 }, { pasillo: true }, { bloques: 3 }],
  balda14: [{ bloques: 4 }, { bloques: 4 }],
  balda22: [{ bloques: 4 }, { bloques: 4 }, { pasillo: true }, { bloques: 4 }],
  neumaticos: [{ bloques: 5 }, { bloques: 5 }],
  // Bulk (Piso) -- bloques grandes en el suelo, pasillos anchos de tránsito
  bulk: [
    { bloques: 4 },
    { bloques: 4 },
    { bloques: 3 },
    { pasillo: true },
    { bloques: 3 },
    { bloques: 3 },
    { bloques: 2 },
  ],
  // Rack Colgantes -- una fila larga, sigue la forma diagonal angosta de la zona
  colgantes: [{ bloques: 6 }],
  mesas: [{ bloques: 1 }],
  carpin: [{ bloques: 1 }],
};

export const PLANTILLA_DEFECTO: FilaZona[] = [{ bloques: 3 }, { bloques: 3 }];

export type FilaRenderizada<T> = { pasillo: true } | { bloques: T[][] };

/** Reparte `items` (los SKU de la zona) entre los bloques de la
 * plantilla, en el orden en que llegan -- lo más parejo posible por
 * bloque. La ESTRUCTURA (filas, bloques, pasillos) es fija por zona;
 * lo único que varía con los datos reales es cuántos SKU caben en cada
 * bloque, para que la misma plantilla sirva tanto para "Hoy" como para
 * "Propuesta" aunque tengan cantidades distintas de SKU.
 */
export function distribuirEnPlantilla<T>(items: T[], plantilla: FilaZona[]): FilaRenderizada<T>[] {
  const totalBloques = plantilla.reduce((acc, f) => ('pasillo' in f ? acc : acc + f.bloques), 0) || 1;
  const porBloque = Math.max(1, Math.ceil(items.length / totalBloques));

  let cursor = 0;
  return plantilla.map((fila) => {
    if ('pasillo' in fila) return { pasillo: true };
    const bloques: T[][] = [];
    for (let b = 0; b < fila.bloques; b++) {
      bloques.push(items.slice(cursor, cursor + porBloque));
      cursor += porBloque;
    }
    return { bloques };
  });
}
