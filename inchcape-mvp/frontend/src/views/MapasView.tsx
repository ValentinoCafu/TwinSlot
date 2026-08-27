import { useState } from 'react';
import { DetalleZona } from '../components/mapas/DetalleZona';
import { MapaOcupacion } from '../components/mapas/MapaOcupacion';
import { PlanoV3Preview } from '../components/mapas/PlanoV3Preview';
import { agruparPorZonaExcel, zonasSinGeometria } from '../components/mapas/ocupacion';
import { PlanoSVG } from '../components/plano/PlanoSVG';
import { EstadoPipeline } from '../components/ui/EstadoPipeline';
import { usePipeline } from '../context/PipelineContext';
import { useZonas, type Zona } from '../api/zonas';
import './MapasView.css';

export function MapasView() {
  const { resultado } = usePipeline();
  const { zonas, error: errorZonas } = useZonas();
  const [zonaDetalle, setZonaDetalle] = useState<Zona | null>(null);

  if (!resultado) {
    return <EstadoPipeline mensaje="Ejecuta el pipeline para comparar el slotting actual contra el recomendado." />;
  }
  if (errorZonas) {
    return <p className="estado-error">No se pudo cargar el plano: {errorZonas}</p>;
  }
  if (!zonas) {
    return <p className="plano-cargando">Cargando geometría del plano…</p>;
  }

  const ocupacionActual = agruparPorZonaExcel(resultado.recomendaciones, 'ZONA_ACTUAL');
  const ocupacionPropuesta = agruparPorZonaExcel(resultado.recomendaciones, 'ZONA_RECOMENDADA');
  const sinGeometria = [
    ...zonasSinGeometria(ocupacionActual, zonas),
    ...zonasSinGeometria(ocupacionPropuesta, zonas),
  ];

  return (
    <div>
      {sinGeometria.length > 0 && (
        <p className="mapas-advertencia">
          <b>Aviso:</b>{' '}
          {[...new Map(sinGeometria.map((o) => [o.clave_excel, o])).values()]
            .map((o) => `${o.count} SKU en "${o.clave_excel}"`)
            .join(', ')}{' '}
          no tienen un polígono confirmado en el plano vectorial (ver <span className="mono">CLAUDE_1.md</span> #8)
          — no se muestran en el mapa, no se les inventa una posición.
        </p>
      )}

      <p className="mapas-ayuda">Haz click en una zona de cualquiera de los dos mapas para ver qué SKU hay ahí.</p>

      <div className="mapas-grid">
        <MapaOcupacion
          titulo="Hoy"
          zonas={zonas}
          recomendaciones={resultado.recomendaciones}
          campo="ZONA_ACTUAL"
          onClickZona={setZonaDetalle}
        />
        <MapaOcupacion
          titulo="Propuesta de slotting"
          zonas={zonas}
          recomendaciones={resultado.recomendaciones}
          campo="ZONA_RECOMENDADA"
          onClickZona={setZonaDetalle}
        />
      </div>

      {zonaDetalle && (
        <DetalleZona zona={zonaDetalle} recomendaciones={resultado.recomendaciones} onClose={() => setZonaDetalle(null)} />
      )}

      <PlanoV3Preview recomendaciones={resultado.recomendaciones} />

      <h2 className="mapas-referencia-titulo">Referencia: geometría y técnica de almacenamiento</h2>
      <PlanoSVG />
    </div>
  );
}
