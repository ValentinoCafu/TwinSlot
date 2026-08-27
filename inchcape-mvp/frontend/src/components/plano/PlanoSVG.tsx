import { useMemo, useRef, useState } from 'react';
import { useZonas, type Zona } from '../../api/zonas';
import { calcularFill, esTextoClaro, ETIQUETA_MODO, type Modo } from './colorModos';
import { PlanoBase } from './PlanoBase';
import './PlanoSVG.css';

interface TooltipState {
  zona: Zona;
  x: number;
  y: number;
}

export function PlanoSVG() {
  const { zonas, distanciaConfirmada, error } = useZonas();
  const [modo, setModo] = useState<Modo>('tec');
  const [seleccionada, setSeleccionada] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const planoRef = useRef<HTMLDivElement>(null);

  const activa = seleccionada ?? tooltip?.zona.id ?? null;

  function mostrarTooltipEnCursor(zona: Zona, e: React.MouseEvent) {
    const caja = planoRef.current?.getBoundingClientRect();
    if (!caja) return;
    setTooltip({ zona, x: e.clientX - caja.left, y: e.clientY - caja.top });
  }

  // El foco por teclado no trae coordenadas de mouse -- se posiciona el
  // tooltip junto al propio polígono enfocado, no junto al cursor.
  function mostrarTooltipEnElemento(zona: Zona, e: React.FocusEvent<SVGPolygonElement>) {
    const caja = planoRef.current?.getBoundingClientRect();
    const elemento = e.currentTarget.getBoundingClientRect();
    if (!caja) return;
    setTooltip({ zona, x: elemento.left - caja.left, y: elemento.top - caja.top });
  }

  function alternarSeleccion(id: string) {
    setSeleccionada((actual) => (actual === id ? null : id));
  }

  if (error) {
    return <p className="plano-error">No se pudo cargar el plano: {error}</p>;
  }
  if (!zonas) {
    return <p className="plano-cargando">Cargando geometría del plano…</p>;
  }

  return (
    <section className="panel">
      <header>
        <h2>Planta · zonificación</h2>
        <span className="note">{ETIQUETA_MODO[modo]}</span>
      </header>
      <div className="panel-body">
        <div className="ctrl" role="group" aria-label="Coloreado">
          {(['tec', 'den', 'dis'] as const).map((m) => (
            <button key={m} aria-pressed={modo === m} onClick={() => setModo(m)}>
              {m === 'tec' ? 'Técnica' : m === 'den' ? 'Densidad' : 'Distancia'}
            </button>
          ))}
        </div>

        <PlanoBase
          zonas={zonas}
          fill={(z) => calcularFill(z, modo, zonas)}
          textoClaro={(z) => esTextoClaro(z, modo, zonas)}
          activa={activa}
          onHoverZona={mostrarTooltipEnCursor}
          onFocusZona={mostrarTooltipEnElemento}
          onLeaveZona={() => setTooltip(null)}
          onClickZona={(z) => alternarSeleccion(z.id)}
          planoRef={planoRef}
        >
          {tooltip && (
            <div className="tip" style={{ left: Math.min(tooltip.x + 14, 340), top: Math.max(tooltip.y - 10, 4) }}>
              <b>{tooltip.zona.nombre}</b>
              Clave Excel · {tooltip.zona.clave_excel}
              <br />
              Distancia al I/O · {tooltip.zona.distancia_m} m
              <br />
              Ubicaciones reales · {tooltip.zona.ubicaciones}
              <br />
              Líneas de picking · {tooltip.zona.lineas_picking || 's/d'}
            </div>
          )}
        </PlanoBase>

        <Leyenda zonas={zonas} modo={modo} />

        <p className="caption">
          {distanciaConfirmada
            ? 'Escala y punto I/O confirmados con una medición real del plano.'
            : 'Distancias medidas al centro del muro de muelles bajo una calibración de referencia (L = 110 m para el recorrido más largo). El punto I/O es un supuesto pendiente de confirmar en planta.'}
        </p>
      </div>

      <TablaZonas zonas={zonas} activa={activa} onHover={setTooltip} onClick={alternarSeleccion} planoRef={planoRef} />
    </section>
  );
}

function Leyenda({ zonas, modo }: { zonas: Zona[]; modo: Modo }) {
  const visibles = useMemo(() => zonas.filter((z) => z.clave_excel !== '—'), [zonas]);
  return (
    <div className="legend">
      {visibles.map((z) => (
        <span key={z.id}>
          <i className="chip" style={{ background: calcularFill(z, modo, zonas) }} />
          {z.nombre}
        </span>
      ))}
    </div>
  );
}

function TablaZonas({
  zonas,
  activa,
  onHover,
  onClick,
  planoRef,
}: {
  zonas: Zona[];
  activa: string | null;
  onHover: (t: TooltipState | null) => void;
  onClick: (id: string) => void;
  planoRef: React.RefObject<HTMLDivElement | null>;
}) {
  return (
    <section className="panel table-panel">
      <header>
        <h2>Zonas</h2>
        <span className="note">{zonas.length} polígonos</span>
      </header>
      <div className="panel-body scroll">
        <table>
          <thead>
            <tr>
              <th>Zona</th>
              <th>Clave Excel</th>
              <th style={{ textAlign: 'right' }}>Dist.</th>
              <th style={{ textAlign: 'right' }}>Ubic.</th>
            </tr>
          </thead>
          <tbody>
            {zonas.map((z) => (
              <tr
                key={z.id}
                className={activa === z.id ? 'on' : undefined}
                onMouseEnter={() => {
                  const caja = planoRef.current?.getBoundingClientRect();
                  if (caja) onHover({ zona: z, x: caja.width / 2, y: 20 });
                }}
                onMouseLeave={() => onHover(null)}
                onClick={() => onClick(z.id)}
              >
                <td>
                  <i className="sq" style={{ background: z.color }} />
                  {z.nombre}
                </td>
                <td className="mono" style={{ fontSize: 11 }}>
                  {z.clave_excel}
                </td>
                <td className="num">{z.clave_excel === '—' ? '—' : `${z.distancia_m} m`}</td>
                <td className="num">{z.ubicaciones}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
