import type { RefObject } from 'react';
import type { Zona } from '../../api/zonas';
import './PlanoSVG.css';

// Geometría decorativa del edificio -- no es dato de negocio (no cambia
// de un lote a otro), así que se queda como constante de frontend, tal
// como en V1 planta-cd-aldeas-vectorial.html.
const CONTORNO_EDIFICIO = '40,10 207,10 564,459 125,592 40,592';
const N_MUELLES = 16;

export interface PlanoBaseProps {
  zonas: Zona[];
  fill: (zona: Zona) => string;
  textoClaro: (zona: Zona) => boolean;
  activa: string | null;
  onHoverZona: (zona: Zona, e: React.MouseEvent) => void;
  onFocusZona: (zona: Zona, e: React.FocusEvent<SVGPolygonElement>) => void;
  onLeaveZona: () => void;
  onClickZona: (zona: Zona) => void;
  planoRef: RefObject<HTMLDivElement | null>;
  children?: React.ReactNode; // overlay posicionado (tooltip), lo decide cada consumidor
}

/** Solo geometría + interacción -- el color y el contenido del tooltip
 * los decide quien lo use (PlanoSVG con técnica/densidad/distancia,
 * MapaOcupacion con SKU actuales/recomendados). */
export function PlanoBase({
  zonas,
  fill,
  textoClaro,
  activa,
  onHoverZona,
  onFocusZona,
  onLeaveZona,
  onClickZona,
  planoRef,
  children,
}: PlanoBaseProps) {
  return (
    <div className="planwrap" ref={planoRef}>
      <svg
        className="plan"
        viewBox="20 0 560 610"
        role="img"
        aria-label="Planta del centro de distribución con las zonas de almacenamiento"
      >
        <GridMetrica />
        <polygon className="plano-contorno" points={CONTORNO_EDIFICIO} />
        <g>
          {zonas.map((zona) => (
            <polygon
              key={zona.id}
              className="zone"
              tabIndex={0}
              points={zona.puntos_svg}
              fill={fill(zona)}
              style={{ strokeWidth: activa === zona.id ? 4 : 1.6 }}
              onMouseMove={(e) => onHoverZona(zona, e)}
              onFocus={(e) => onFocusZona(zona, e)}
              onMouseLeave={onLeaveZona}
              onBlur={onLeaveZona}
              onClick={() => onClickZona(zona)}
            >
              <title>{zona.nombre}</title>
            </polygon>
          ))}
        </g>
        <Muelles />
        <circle className="io" cx={46} cy={300} r={7} />
        <text x={58} y={303} className="lbl sm" fontSize={9} fill="#1B2025">
          I/O
        </text>
        <g>
          {zonas.map((zona) => (
            <text
              key={zona.id}
              className="lbl"
              x={zona.label_x}
              y={zona.label_y}
              fontSize={zona.label_fs}
              fill={textoClaro(zona) ? '#F5F3EE' : '#1B2025'}
              style={{ stroke: textoClaro(zona) ? '#1B2025' : '#FFFFFF' }}
              textAnchor="middle"
              transform={zona.label_rot ? `rotate(${zona.label_rot} ${zona.label_x} ${zona.label_y})` : undefined}
            >
              {zona.nombre}
            </text>
          ))}
        </g>
        <Escala />
      </svg>
      {children}
    </div>
  );
}

function GridMetrica() {
  const verticales = [];
  for (let x = 40; x < 580; x += 40) verticales.push(<line key={`v${x}`} x1={x} y1={0} x2={x} y2={610} />);
  const horizontales = [];
  for (let y = 0; y < 610; y += 40) horizontales.push(<line key={`h${y}`} x1={20} y1={y} x2={580} y2={y} />);
  return (
    <g className="grid-m">
      {verticales}
      {horizontales}
    </g>
  );
}

function Muelles() {
  return (
    <g>
      {Array.from({ length: N_MUELLES }, (_, i) => {
        const y = 70 + i * 30;
        return (
          <g key={i}>
            <rect className="dock" x={31} y={y} width={11} height={15} />
            <text className="docknum" x={36.5} y={y + 11} textAnchor="middle">
              {i + 1}
            </text>
          </g>
        );
      })}
    </g>
  );
}

function Escala() {
  return (
    <g className="lbl sm" fontSize={8.5} fill="#3A434B">
      <line x1={400} y1={575} x2={480} y2={575} stroke="#1B2025" strokeWidth={1.6} strokeLinecap="square" />
      <line x1={400} y1={571} x2={400} y2={579} stroke="#1B2025" strokeWidth={1.6} />
      <line x1={480} y1={571} x2={480} y2={579} stroke="#1B2025" strokeWidth={1.6} />
      <text x={440} y={569} textAnchor="middle">
        ≈ 20 m
      </text>
    </g>
  );
}
