import { apiFetch, API_BASE_URL, ApiError } from './config';

export type Operador = '==' | '!=' | '>' | '>=' | '<' | '<=';
export type TipoRegla = 'atributo' | 'incompatibilidad' | 'umbral';

// Coinciden 1:1 con app/dominio/reglas/modelos.py del backend.
export interface ReglaAtributoDef {
  campo: string;
  operador: Operador;
  valor: number | string;
  zona_permitida: string | null;
  zona_prohibida: string | null;
}

export interface ReglaIncompatibilidadDef {
  familia_a: string;
  familia_b: string;
  modo: 'misma_zona_prohibida';
}

export interface ReglaUmbralDef {
  campo_evaluado: string;
  operador: Operador;
  valor_umbral: number;
  accion: string;
}

export type DefinicionRegla = ReglaAtributoDef | ReglaIncompatibilidadDef | ReglaUmbralDef;

export interface Regla {
  id: string;
  tipo: TipoRegla;
  nombre: string;
  definicion: DefinicionRegla;
  activa: boolean;
  justificacion: string;
}

export function fetchReglas(): Promise<Regla[]> {
  return apiFetch<Regla[]>('/reglas');
}

export function crearRegla(regla: Regla): Promise<Regla> {
  return apiFetch<Regla>('/reglas', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(regla),
  });
}

export function actualizarRegla(id: string, regla: Regla): Promise<Regla> {
  return apiFetch<Regla>(`/reglas/${encodeURIComponent(id)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(regla),
  });
}

export async function eliminarRegla(id: string): Promise<void> {
  const respuesta = await fetch(`${API_BASE_URL}/reglas/${encodeURIComponent(id)}`, { method: 'DELETE' });
  if (!respuesta.ok && respuesta.status !== 404) {
    throw new ApiError(respuesta.status, respuesta.statusText);
  }
}

export function nuevoIdRegla(): string {
  return `R-${Date.now().toString(36).toUpperCase()}`;
}
