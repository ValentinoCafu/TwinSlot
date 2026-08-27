import { useState } from 'react';
import { DetalleZona } from '../components/mapas/DetalleZona';
import { MapaOcupacion } from '../components/mapas/MapaOcupacion';
import { EstadoPipeline } from '../components/ui/EstadoPipeline';
import { usePipeline } from '../context/PipelineContext';
import { useZonas, type Zona } from '../api/zonas';

export function EstadoActualView() {
  const { resultado } = usePipeline();
  const { zonas, error } = useZonas();
  const [zonaDetalle, setZonaDetalle] = useState<Zona | null>(null);

  if (!resultado) {
    return <EstadoPipeline mensaje="Ejecuta el pipeline para ver la situación actual del almacén." />;
  }
  if (error) return <p className="estado-error">No se pudo cargar el plano: {error}</p>;
  if (!zonas) return <p className="plano-cargando">Cargando geometría del plano…</p>;

  return (
    <>
      <MapaOcupacion
        titulo="Situación actual del almacén"
        zonas={zonas}
        recomendaciones={resultado.recomendaciones}
        campo="ZONA_ACTUAL"
        onClickZona={setZonaDetalle}
      />
      {zonaDetalle && (
        <DetalleZona zona={zonaDetalle} recomendaciones={resultado.recomendaciones} onClose={() => setZonaDetalle(null)} />
      )}
    </>
  );
}
