import { useMemo, useRef, useState } from 'react';
import type { RecomendacionSKU } from '../../api/pipeline';
import type { Zona } from '../../api/zonas';
import { PlanoBase } from '../plano/PlanoBase';
import '../plano/PlanoSVG.css';
import { agruparPorZonaExcel, agruparSkusPorZonaExcel, esZonaPrimariaParaSuClave, type OcupacionZona } from './ocupacion';
import { ESPACIOS_ZONA } from './espaciosZona';
import { GrillaSkus } from './GrillaSkus';
import './MapaOcupacion.css';

interface TooltipState {
  zona: Zona;
  ocupacion?: OcupacionZona;
  x: number;
  y: number;
}

interface HoverGridState {
  zona: Zona;
  left: number;
  top: number;
}

export function MapaOcupacion({
  titulo,
  zonas,
  recomendaciones,
  campo,
  onClickZona,
}: {
  titulo: string;
  zonas: Zona[];
  recomendaciones: RecomendacionSKU[];
  campo: 'ZONA_ACTUAL' | 'ZONA_RECOMENDADA';
  onClickZona: (zona: Zona) => void;
}) {
  const ocupacion = agruparPorZonaExcel(recomendaciones, campo);
  const skusPorZonaExcel = useMemo(() => agruparSkusPorZonaExcel(recomendaciones, campo), [recomendaciones, campo]);
  const maxCount = Math.max(...[...ocupacion.values()].map((o) => o.count), 1);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const [hoverGrid, setHoverGrid] = useState<HoverGridState | null>(null);
  const planoRef = useRef<HTMLDivElement>(null);

  const rangoRotacion = useMemo(() => {
    const valores = recomendaciones.map((r) => r.ROTACION_6M);
    return { min: Math.min(...valores), max: Math.max(...valores) };
  }, [recomendaciones]);

  function conteoDe(zona: Zona): number {
    if (zona.clave_excel === '—' || !esZonaPrimariaParaSuClave(zona)) return 0;
    return ocupacion.get(zona.clave_excel)?.count ?? 0;
  }

  function fill(zona: Zona): string {
    const count = conteoDe(zona);
    if (count === 0) return '#FFFFFF';
    const pct = Math.round(14 + (count / maxCount) * 86);
    return `color-mix(in srgb, #0F5F8F ${pct}%, #DCE6ED)`;
  }

  function textoClaro(zona: Zona): boolean {
    return conteoDe(zona) / maxCount > 0.55;
  }

  function ocupacionDe(zona: Zona): OcupacionZona | undefined {
    return esZonaPrimariaParaSuClave(zona) ? ocupacion.get(zona.clave_excel) : undefined;
  }

  /** Solo zonas con capacidad real definida (`espaciosZona.ts`) y que son
   * la primaria de su clave_excel muestran la grilla al pasar el mouse --
   * el resto se queda con el tooltip de texto simple. */
  function tieneGridDefinida(zona: Zona): boolean {
    return Boolean(ESPACIOS_ZONA[zona.id]) && esZonaPrimariaParaSuClave(zona);
  }

  function actualizarHoverGrid(zona: Zona, elemento: Element) {
    if (!tieneGridDefinida(zona)) {
      setHoverGrid(null);
      return;
    }
    const cajaPlano = planoRef.current?.getBoundingClientRect();
    const cajaZona = elemento.getBoundingClientRect();
    if (!cajaPlano) return;
    setHoverGrid({ zona, left: cajaZona.left - cajaPlano.left, top: cajaZona.top - cajaPlano.top });
  }

  function mostrarEnCursor(zona: Zona, e: React.MouseEvent) {
    const caja = planoRef.current?.getBoundingClientRect();
    if (!caja) return;
    setTooltip({ zona, ocupacion: ocupacionDe(zona), x: e.clientX - caja.left, y: e.clientY - caja.top });
    actualizarHoverGrid(zona, e.currentTarget);
  }

  function mostrarEnElemento(zona: Zona, e: React.FocusEvent<SVGPolygonElement>) {
    const caja = planoRef.current?.getBoundingClientRect();
    const el = e.currentTarget.getBoundingClientRect();
    if (!caja) return;
    setTooltip({ zona, ocupacion: ocupacionDe(zona), x: el.left - caja.left, y: el.top - caja.top });
    actualizarHoverGrid(zona, e.currentTarget);
  }

  function ocultarTodo() {
    setTooltip(null);
    setHoverGrid(null);
  }

  return (
    <section className="panel">
      <header>
        <h2>{titulo}</h2>
        <span className="note">{recomendaciones.length} SKU</span>
      </header>
      <div className="panel-body">
        <PlanoBase
          zonas={zonas}
          fill={fill}
          textoClaro={textoClaro}
          activa={tooltip?.zona.id ?? null}
          onHoverZona={mostrarEnCursor}
          onFocusZona={mostrarEnElemento}
          onLeaveZona={ocultarTodo}
          onClickZona={onClickZona}
          planoRef={planoRef}
        >
          {tooltip && (
            <div className="tip" style={{ left: Math.min(tooltip.x + 14, 300), top: Math.max(tooltip.y - 10, 4) }}>
              <b>{tooltip.zona.nombre}</b>
              {tooltip.zona.clave_excel === '—' ? (
                'Sin equivalente en el Excel de zonas (LAYOUT_CD)'
              ) : (
                <>
                  Clave Excel · {tooltip.zona.clave_excel}
                  <br />
                  SKU aquí · {tooltip.ocupacion?.count ?? 0}
                  <br />
                  <i>Click para ver detalle</i>
                </>
              )}
            </div>
          )}
          {hoverGrid && (
            <div className="espacios-hover" style={{ left: hoverGrid.left, top: hoverGrid.top }}>
              <GrillaSkus
                zonaId={hoverGrid.zona.id}
                skus={skusPorZonaExcel.get(hoverGrid.zona.clave_excel) ?? []}
                estado={() => 'normal'}
                modo="rotacion"
                rangoRotacion={rangoRotacion}
              />
            </div>
          )}
        </PlanoBase>
      </div>
    </section>
  );
}
