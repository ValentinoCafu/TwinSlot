import { useMemo, useState } from 'react';
import type { RecomendacionSKU } from '../../api/pipeline';
import { colorCalor } from './GrillaSkus';
import { LAYOUT_V3, ZONAS_V3 } from './layoutV3';
import './PlanoV3Preview.css';

type ModoColorV3 = 'ocupacion' | 'rotacion';

/** Vista previa del trazado real (`layout inchape v3.svg`) -- muestra
 * las zonas ya trazadas con su polígono y posiciones de espacio reales
 * (no una grilla CSS aproximada), coloreadas por ocupado/libre o por
 * calor de rotación, contra los SKU reales del pipeline. Es un
 * comparativo preliminar mientras se completan las 13 zonas -- ver
 * `LAYOUT-SVG-V3.md`. */
export function PlanoV3Preview({ recomendaciones }: { recomendaciones: RecomendacionSKU[] }) {
  const [hover, setHover] = useState<{ id: string; texto: string } | null>(null);
  const [modo, setModo] = useState<ModoColorV3>('ocupacion');

  const porZona = useMemo(() => {
    return ZONAS_V3.map(({ nombreSvg, zonaId, claveExcel }) => {
      const zona = LAYOUT_V3.zonas[nombreSvg];
      const skus = claveExcel ? recomendaciones.filter((r) => r.ZONA_ACTUAL === claveExcel) : [];
      return { nombreSvg, zonaId, zona, skus };
    }).filter((z) => z.zona);
  }, [recomendaciones]);

  const rangoRotacion = useMemo(() => {
    const valores = recomendaciones.map((r) => r.ROTACION_6M);
    return { min: Math.min(...valores), max: Math.max(...valores) };
  }, [recomendaciones]);

  const totalEspacios = porZona.reduce((acc, z) => acc + (z.zona?.espacios.length ?? 0), 0);
  const totalOcupados = porZona.reduce((acc, z) => acc + Math.min(z.skus.length, z.zona?.espacios.length ?? 0), 0);

  return (
    <section className="panel plano-v3">
      <header>
        <h2>Plano real (v3)</h2>
        <span className="note">{porZona.length} de 13 zonas trazadas</span>
      </header>
      <div className="panel-body">
        <p className="plano-v3-nota">
          Geometría real escaneada de <span className="mono">layout inchape v3.svg</span> — polígonos y posiciones de
          espacio reales, no una aproximación. Trazado en progreso: {totalOcupados} ocupados de {totalEspacios} espacios
          definidos hasta ahora.
        </p>

        <div className="ctrl" role="group" aria-label="Color del plano real">
          <button aria-pressed={modo === 'ocupacion'} onClick={() => setModo('ocupacion')}>
            Por ocupación
          </button>
          <button aria-pressed={modo === 'rotacion'} onClick={() => setModo('rotacion')}>
            Por rotación
          </button>
        </div>

        <div className="planwrap plano-v3-wrap">
          <svg className="plan" viewBox={LAYOUT_V3.view_box ?? '0 0 1304 683'} role="img" aria-label="Plano real trazado">
            {porZona.map(({ zonaId, zona, skus }) => {
              if (!zona) return null;
              return (
                <g key={zonaId}>
                  <path d={zona.boundary_d ?? undefined} className="plano-v3-borde" />
                  {zona.espacios.map((e, i) => {
                    const sku = skus[i];
                    const ocupado = Boolean(sku);
                    const estilo =
                      ocupado && modo === 'rotacion' && rangoRotacion.max > rangoRotacion.min
                        ? { fill: colorCalor((sku.ROTACION_6M - rangoRotacion.min) / (rangoRotacion.max - rangoRotacion.min)) }
                        : undefined;
                    return (
                      <rect
                        key={e.id}
                        x={e.x}
                        y={e.y}
                        width={e.ancho}
                        height={e.alto}
                        style={estilo}
                        className={ocupado ? 'plano-v3-espacio ocupado' : 'plano-v3-espacio libre'}
                        onMouseEnter={() =>
                          setHover({
                            id: e.id,
                            texto: ocupado ? `${sku.SKU} · ${sku.FAMILIA} · rotación 6m: ${sku.ROTACION_6M}` : 'Espacio libre',
                          })
                        }
                        onMouseLeave={() => setHover(null)}
                      />
                    );
                  })}
                  <text x={zona.espacios[0]?.x ?? 0} y={(zona.espacios[0]?.y ?? 0) - 4} className="plano-v3-etiqueta">
                    {zona.titulo}
                  </text>
                </g>
              );
            })}
          </svg>
          {hover && <div className="plano-v3-tip">{hover.texto}</div>}
        </div>
      </div>
    </section>
  );
}
