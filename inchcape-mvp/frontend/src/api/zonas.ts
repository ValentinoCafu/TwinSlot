import { useEffect, useState } from 'react';
import { apiFetch, ApiError } from './config';

// Coincide 1:1 con app/schemas/zonas.py del backend.
export interface Zona {
  id: string;
  nombre: string;
  clave_excel: string;
  distancia_m: number;
  ubicaciones: string;
  lineas_picking: number;
  color: string;
  puntos_svg: string;
  label_x: number;
  label_y: number;
  label_fs: number;
  label_rot: number;
  texto_claro: boolean;
}

export interface RespuestaZonas {
  zonas: Zona[];
  distancia_absoluta_confirmada: boolean;
}

export function fetchZonas(): Promise<RespuestaZonas> {
  return apiFetch<RespuestaZonas>('/zonas');
}

/** Compartido entre PlanoSVG y MapaOcupacion -- geometría estática, se
 * pide una sola vez por vista que la monte, nunca se duplica la lógica
 * de fetch/estado de carga. */
export function useZonas() {
  const [zonas, setZonas] = useState<Zona[] | null>(null);
  const [distanciaConfirmada, setDistanciaConfirmada] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchZonas()
      .then((r) => {
        setZonas(r.zonas);
        setDistanciaConfirmada(r.distancia_absoluta_confirmada);
      })
      .catch((e: unknown) => setError(e instanceof ApiError ? e.detail : 'No se pudo conectar con el backend.'));
  }, []);

  return { zonas, distanciaConfirmada, error };
}
