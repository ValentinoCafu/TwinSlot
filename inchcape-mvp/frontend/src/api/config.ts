// Correr todo en local durante la demo es la opción de menor riesgo
// (propuesta-arquitectura-tecnica-react-fastapi.md §7) -- por eso no hay
// variable de entorno todavía: agregar VITE_API_BASE_URL el día que se
// necesite apuntar a un backend desplegado, no antes.
export const API_BASE_URL = 'http://127.0.0.1:8000';

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const respuesta = await fetch(`${API_BASE_URL}${path}`, init);
  if (!respuesta.ok) {
    const cuerpo = await respuesta.json().catch(() => ({ detail: respuesta.statusText }));
    throw new ApiError(respuesta.status, cuerpo.detail ?? respuesta.statusText);
  }
  return respuesta.json() as Promise<T>;
}
