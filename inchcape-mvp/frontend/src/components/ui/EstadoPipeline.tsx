import { usePipeline } from '../../context/PipelineContext';
import { PipelineChecklist } from './PipelineChecklist';
import './ui.css';

/** Estado vacío/error compartido: se muestra en cualquier vista que
 * necesite `resultado` y todavía no lo tiene. Un solo botón dispara
 * POST /pipeline/ejecutar -- no hay auto-ejecución porque correr el
 * optimizador + KMeans + reglas no es gratis y el usuario debe decidir
 * cuándo recalcular, no que pase solo. */
export function EstadoPipeline({ mensaje }: { mensaje: string }) {
  const { cargando, error, ejecutar } = usePipeline();

  return (
    <div className="estado-vacio">
      <p style={{ marginBottom: 14 }}>{mensaje}</p>
      {error && <p className="estado-error" style={{ marginBottom: 14 }}>{error}</p>}
      <button className="boton" disabled={cargando} onClick={() => ejecutar()}>
        {cargando ? 'Calculando…' : 'Ejecutar pipeline'}
      </button>
      {cargando && <PipelineChecklist />}
    </div>
  );
}
