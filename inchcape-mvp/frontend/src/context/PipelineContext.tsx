import { createContext, useCallback, useContext, useState, type ReactNode } from 'react';
import { ApiError } from '../api/config';
import { ejecutarPipeline, type PesosScore, type RespuestaPipeline } from '../api/pipeline';

interface PipelineContextValue {
  resultado: RespuestaPipeline | null;
  // el resultado justo anterior a la última ejecución -- permite a la
  // vista "Puntuación" mostrar qué SKU cambiaron de zona recomendada al
  // ajustar los pesos, sin que cada vista tenga que guardar su propia copia.
  anterior: RespuestaPipeline | null;
  cargando: boolean;
  error: string | null;
  ejecutar: (pesos?: PesosScore, porcentajeMaxMovimiento?: number) => Promise<void>;
}

const PipelineContext = createContext<PipelineContextValue | null>(null);

export function PipelineProvider({ children }: { children: ReactNode }) {
  const [resultado, setResultado] = useState<RespuestaPipeline | null>(null);
  const [anterior, setAnterior] = useState<RespuestaPipeline | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ejecutar = useCallback(async (pesos?: PesosScore, porcentajeMaxMovimiento?: number) => {
    setCargando(true);
    setError(null);
    try {
      const nuevo = await ejecutarPipeline(pesos, porcentajeMaxMovimiento);
      setResultado((previo) => {
        setAnterior(previo);
        return nuevo;
      });
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : 'No se pudo conectar con el backend.');
    } finally {
      setCargando(false);
    }
  }, []);

  return (
    <PipelineContext.Provider value={{ resultado, anterior, cargando, error, ejecutar }}>
      {children}
    </PipelineContext.Provider>
  );
}

export function usePipeline(): PipelineContextValue {
  const ctx = useContext(PipelineContext);
  if (!ctx) throw new Error('usePipeline debe usarse dentro de <PipelineProvider>');
  return ctx;
}
