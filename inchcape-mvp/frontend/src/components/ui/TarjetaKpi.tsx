import './ui.css';

export function TarjetaKpi({
  etiqueta,
  valor,
  subtexto,
  tono,
  subtextoAcento,
}: {
  etiqueta: string;
  valor: string;
  subtexto?: string;
  tono?: 'positivo' | 'riesgo';
  /** Resalta el subtexto en el color de acento -- para el "con la
   * propuesta: -X%" que acompaña al KPI de diagnóstico (hoy). */
  subtextoAcento?: boolean;
}) {
  return (
    <div className={`kpi-card${tono ? ` kpi-${tono}` : ''}`}>
      <span className="kpi-etiqueta">{etiqueta}</span>
      <span className="kpi-valor mono">{valor}</span>
      {subtexto && <span className={subtextoAcento ? 'kpi-sub kpi-sub-acento' : 'kpi-sub'}>{subtexto}</span>}
    </div>
  );
}
