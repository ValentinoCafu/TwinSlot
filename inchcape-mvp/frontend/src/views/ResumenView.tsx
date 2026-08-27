import { PlanoV3Preview } from '../components/mapas/PlanoV3Preview';
import { usePipeline } from '../context/PipelineContext';
import { EstadoActualView } from './EstadoActualView';
import { KpisPrincipales } from './KpisPrincipales';

/** Vista de aterrizaje (DISENO-FRONTEND.md §1.2): diagnóstico de hoy
 * primero (KPIs), mapa de calor de ocupación actual debajo. */
export function ResumenView() {
  const { resultado } = usePipeline();
  return (
    <div>
      <KpisPrincipales />
      <EstadoActualView />
      {resultado && <PlanoV3Preview recomendaciones={resultado.recomendaciones} />}
    </div>
  );
}
