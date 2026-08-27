import { useState } from 'react';
import { PipelineProvider } from './context/PipelineContext';
import { useTema } from './hooks/useTema';
import { ResumenView } from './views/ResumenView';
import { IngestaView } from './views/IngestaView';
import { SkuSlottingView } from './views/SkuSlottingView';
import { MapasView } from './views/MapasView';
import { ReglasView } from './views/ReglasView';
import './App.css';

type Vista = 'resumen' | 'ingesta' | 'skus' | 'reglas' | 'mapas';

const SECCIONES: { id: Vista; etiqueta: string; descripcion: string }[] = [
  { id: 'resumen', etiqueta: 'Resumen', descripcion: 'Diagnóstico de hoy' },
  { id: 'ingesta', etiqueta: 'Carga de datos', descripcion: 'Excel + mapeo' },
  { id: 'skus', etiqueta: 'SKU · Slotting', descripcion: 'Estado y explicabilidad' },
  { id: 'reglas', etiqueta: 'Reglas', descripcion: 'Restricciones por zona' },
  { id: 'mapas', etiqueta: 'Mapas', descripcion: 'Hoy vs. propuesta' },
];

export default function App() {
  const [vista, setVista] = useState<Vista>('resumen');
  const activa = SECCIONES.find((s) => s.id === vista)!;
  const { tema, setTema } = useTema();

  return (
    <PipelineProvider>
      <div className="shell">
        <aside className="sidebar">
          <div className="sidebar-brand">
            <span className="sidebar-brand-badge">Sombra digital</span>
            <span className="sidebar-brand-sub">CD Aldeas · Villa El Salvador</span>
          </div>
          <nav aria-label="Secciones">
            {SECCIONES.map((s) => (
              <button
                key={s.id}
                className={s.id === vista ? 'sidebar-link activa' : 'sidebar-link'}
                onClick={() => setVista(s.id)}
              >
                {s.etiqueta}
              </button>
            ))}
          </nav>
          <div className="ctrl sidebar-tema" role="group" aria-label="Tema de la interfaz">
            {([
              { valor: null, etiqueta: 'Sistema' },
              { valor: 'light', etiqueta: 'Claro' },
              { valor: 'dark', etiqueta: 'Oscuro' },
            ] as const).map((op) => (
              <button key={op.etiqueta} aria-pressed={tema === op.valor} onClick={() => setTema(op.valor)}>
                {op.etiqueta}
              </button>
            ))}
          </div>
          <p className="sidebar-nota">
            Ninguna recomendación se escribe automáticamente al WMS — siempre revisa y aplica una persona.
          </p>
        </aside>

        <div className="shell-content">
          <header className="shell-header">
            <h1>{activa.etiqueta}</h1>
            <p>{activa.descripcion}</p>
          </header>
          <main>
            {vista === 'resumen' && <ResumenView />}
            {vista === 'ingesta' && <IngestaView />}
            {vista === 'skus' && <SkuSlottingView />}
            {vista === 'reglas' && <ReglasView />}
            {vista === 'mapas' && <MapasView />}
          </main>
        </div>
      </div>
    </PipelineProvider>
  );
}
