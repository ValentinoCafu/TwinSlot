import { EstadoPipeline } from '../components/ui/EstadoPipeline';
import { TarjetaKpi } from '../components/ui/TarjetaKpi';
import { usePipeline } from '../context/PipelineContext';

/** Los 2 KPIs que el caso ya declaró en RESUMEN (ver FEATURES-Y-KPIS.md).
 * Vista de diagnóstico: el número grande es el de HOY, no el optimizado
 * -- la propuesta aparece como nota de acento, es el incentivo para ir
 * a "SKU · Slotting", no el protagonista (ver DISENO-FRONTEND.md §1.2). */
export function KpisPrincipales() {
  const { resultado } = usePipeline();
  if (!resultado) return <EstadoPipeline mensaje="Ejecuta el pipeline para ver los KPIs del caso." />;

  const { kpis } = resultado;
  return (
    <div className="grid-kpi grid-kpi-principal">
      <TarjetaKpi
        etiqueta="Productividad hoy"
        valor={`${kpis.productividad_actual_lineas_hh.toFixed(2)} líneas/HH`}
        subtexto={`con la propuesta: ${kpis.productividad_optimizada_lineas_hh.toFixed(2)} líneas/HH`}
        subtextoAcento
      />
      <TarjetaKpi
        etiqueta="Tiempo promedio de picking hoy"
        valor={`${kpis.tiempo_promedio_actual_min_pedido.toFixed(2)} min/pedido`}
        subtexto={`con la propuesta: ${kpis.tiempo_promedio_optimizado_min_pedido.toFixed(2)} min/pedido (−${kpis.reduccion_porcentaje.toFixed(1)}%)`}
        subtextoAcento
      />
    </div>
  );
}
