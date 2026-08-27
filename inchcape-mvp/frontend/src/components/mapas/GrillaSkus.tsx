import type { RecomendacionSKU } from '../../api/pipeline';
import { distribuirEnPlantilla, PLANTILLAS_ZONA, PLANTILLA_DEFECTO } from './plantillasZona';
import { ESPACIOS_ZONA, distribuirEnEspacios } from './espaciosZona';
import './GrillaSkus.css';

export type EstadoSlot = 'entra' | 'sale' | 'normal';
export type ModoColorGrilla = 'movimiento' | 'rotacion';

export function colorCalor(intensidad: number): string {
  const pct = Math.round(Math.max(0, Math.min(1, intensidad)) * 100);
  return `color-mix(in srgb, #0F5F8F ${pct}%, #DCE6ED)`;
}

/** Disposición tipo "asientos de cine". Para las zonas con capacidad
 * real definida (`espaciosZona.ts`) muestra ocupados + libres sobre un
 * total fijo; para el resto cae al reparto ilustrativo sin capacidad
 * fija (`plantillasZona.ts`) -- ninguna zona sin datos reales se oculta,
 * pero tampoco se le inventa un total de espacios que no fue definido.
 */
export function GrillaSkus({
  zonaId,
  skus,
  estado,
  vacioTexto = 'Sin SKU en esta zona.',
  modo = 'movimiento',
  rangoRotacion,
}: {
  zonaId: string;
  skus: RecomendacionSKU[];
  estado: (sku: RecomendacionSKU) => EstadoSlot;
  vacioTexto?: string;
  modo?: ModoColorGrilla;
  /** min/max de ROTACION_6M sobre TODO el catálogo, para que el color de
   * calor sea comparable entre zonas -- lo calcula el padre una sola vez. */
  rangoRotacion?: { min: number; max: number };
}) {
  const espacios = ESPACIOS_ZONA[zonaId];

  if (espacios) {
    const { filas, ocupados, libres, desbordados } = distribuirEnEspacios(skus, espacios);
    return (
      <div>
        <p className="grilla-resumen">
          <b>{ocupados}</b> ocupados · <b>{libres}</b> libres · {ocupados + libres} espacios definidos
        </p>
        {desbordados > 0 && (
          <p className="grilla-desbordado">
            ⚠️ {desbordados} SKU no caben en la capacidad definida para esta zona -- revisa el diseño de espacios.
          </p>
        )}
        <div className="grilla-zona">
          {filas.map((fila, i) =>
            'pasillo' in fila ? (
              <div key={i} className="grilla-pasillo" aria-hidden="true" />
            ) : (
              <div key={i} className="grilla-fila">
                {fila.bloques.map((bloque, j) => (
                  <div key={j} className="grilla-bloque">
                    {bloque.map((subfila, k) => (
                      <div key={k} className="grilla-subfila" style={{ gridTemplateColumns: `repeat(${subfila.length}, 1fr)` }}>
                        {subfila.map((slot, l) =>
                          slot.ocupado ? (
                            <SlotOcupado key={slot.item.SKU} r={slot.item} estado={estado} modo={modo} rangoRotacion={rangoRotacion} />
                          ) : (
                            <span key={l} className="slot slot-libre" title="Espacio libre" />
                          ),
                        )}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            ),
          )}
        </div>
      </div>
    );
  }

  if (skus.length === 0) {
    return <p className="grilla-vacia">{vacioTexto}</p>;
  }

  const plantilla = PLANTILLAS_ZONA[zonaId] ?? PLANTILLA_DEFECTO;
  const filas = distribuirEnPlantilla(skus, plantilla);

  return (
    <div>
      <p className="grilla-nota-sin-capacidad">
        Esta zona todavía no tiene una capacidad total definida -- se muestran solo los {skus.length} SKU actuales,
        sin espacios libres.
      </p>
      <div className="grilla-zona">
        {filas.map((fila, i) =>
          'pasillo' in fila ? (
            <div key={i} className="grilla-pasillo" aria-hidden="true" />
          ) : (
            <div key={i} className="grilla-fila">
              {fila.bloques.map((bloque, j) => (
                <div key={j} className="grilla-bloque">
                  <div className="grilla-subfila-auto">
                    {bloque.map((r) => (
                      <SlotOcupado key={r.SKU} r={r} estado={estado} modo={modo} rangoRotacion={rangoRotacion} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ),
        )}
      </div>
    </div>
  );
}

function SlotOcupado({
  r,
  estado,
  modo,
  rangoRotacion,
}: {
  r: RecomendacionSKU;
  estado: (sku: RecomendacionSKU) => EstadoSlot;
  modo: ModoColorGrilla;
  rangoRotacion?: { min: number; max: number };
}) {
  const e = estado(r);
  const estilo =
    modo === 'rotacion' && rangoRotacion && rangoRotacion.max > rangoRotacion.min
      ? { background: colorCalor((r.ROTACION_6M - rangoRotacion.min) / (rangoRotacion.max - rangoRotacion.min)) }
      : undefined;
  return (
    <span
      className={modo === 'movimiento' ? `slot slot-${e}` : 'slot'}
      style={estilo}
      title={`${r.SKU} · ${r.FAMILIA} · rotación 6m: ${r.ROTACION_6M} · ${r.MOVIMIENTO}`}
    >
      <span className="slot-sku">{r.SKU.replace('SKU', '')}</span>
      {modo === 'movimiento' && e === 'entra' && <span className="slot-flecha">↓</span>}
      {modo === 'movimiento' && e === 'sale' && <span className="slot-flecha">↑</span>}
    </span>
  );
}
