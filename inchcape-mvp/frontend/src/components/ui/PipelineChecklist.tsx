import './ui.css';

const ETAPAS = [
  'Consolidando pedidos por SKU',
  'Calculando impacto operativo y score de prioridad',
  'Entrenando clustering ML (K-Means)',
  'Calculando capacidad disponible por zona',
  'Aplicando reglas de negocio activas',
  'Optimizando asignación de zonas (CBC)',
  'Calculando KPIs de productividad y tiempo',
];

/** Checklist honesto: el backend responde en una sola llamada síncrona, así
 * que no hay progreso real por etapa que reportar -- se listan las etapas
 * reales del pipeline (ver dominio/pipeline.py) todas "en curso" a la vez,
 * en vez de simular un avance que no existe. */
export function PipelineChecklist({ etapaExtra }: { etapaExtra?: string }) {
  const etapas = etapaExtra ? [etapaExtra, ...ETAPAS] : ETAPAS;
  return (
    <ul className="pipeline-checklist" aria-live="polite">
      {etapas.map((e) => (
        <li key={e}>
          <span className="pipeline-checklist-spinner" aria-hidden="true" />
          {e}
        </li>
      ))}
    </ul>
  );
}
