import { API_BASE_URL, ApiError, apiFetch } from './config';

export interface MapeoTabla {
  hoja: string;
  columnas: Record<string, string>; // canónico -> origen
}
export type Mapeo = Record<string, MapeoTabla>;

export interface FilaRechazada {
  tabla: string;
  fila: number;
  motivo: string;
  datos?: Record<string, unknown> | null;
}
export interface RespuestaIngesta {
  filas_aceptadas: number;
  filas_rechazadas: FilaRechazada[];
  resumen_por_tabla: Record<string, { aceptadas: number; rechazadas: number }>;
}

export function fetchMapeo(): Promise<Mapeo> {
  return apiFetch<Mapeo>('/ingesta/mapeo');
}

/** `archivos`: un único Excel (.xlsx/.xls) con las 6 hojas, o varios
 * CSV sueltos (uno por tabla) -- el backend decide el modo según la
 * cantidad y extensión (ver `app/api/routers/ingesta.py`). */
export async function subirIngesta(archivos: File[], mapeo: Mapeo): Promise<RespuestaIngesta> {
  const form = new FormData();
  for (const archivo of archivos) form.append('archivos', archivo);
  form.append('mapeo', JSON.stringify(mapeo));
  const respuesta = await fetch(`${API_BASE_URL}/ingesta`, { method: 'POST', body: form });
  if (!respuesta.ok) {
    const cuerpo = await respuesta.json().catch(() => ({ detail: respuesta.statusText }));
    throw new ApiError(respuesta.status, cuerpo.detail ?? respuesta.statusText);
  }
  return respuesta.json();
}
