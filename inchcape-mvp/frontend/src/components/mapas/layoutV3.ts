import datos from '../../data/layoutV3.json';

/** Geometría real trazada a mano en `layout inchape v3.svg` (Synoptic
 * Designer) -- ver `LAYOUT-SVG-V3.md` en la raíz del proyecto para el
 * contrato completo y cómo regenerar `data/layoutV3.json` cuando llegue
 * una versión más completa (`scripts/extraer_layout_svg.py`).
 *
 * A diferencia de `espaciosZona.ts` (forma ilustrativa + capacidad de
 * tu Excel), esto es la forma y posición REAL de cada espacio dentro
 * del polígono real de la zona -- pero solo cubre las zonas que ya
 * están trazadas, y sus totales NO coinciden todavía con los de Excel
 * (es un trazado en progreso, ver documentación).
 */

export interface EspacioV3 {
  id: string;
  x: number;
  y: number;
  ancho: number;
  alto: number;
}

export interface ZonaV3 {
  titulo: string | null;
  boundary_d: string | null;
  espacios: EspacioV3[];
}

interface LayoutV3 {
  view_box: string | null;
  zonas: Record<string, ZonaV3>;
}

export const LAYOUT_V3 = datos as LayoutV3;

/** Nombre de zona en el SVG trazado -> id de zona / clave_excel que ya
 * usa el resto de la app, para poder cruzar contra SKU reales. `doble`
 * nunca tiene SKU real (sin equivalente en LAYOUT_CD, ver README
 * backend §3.1); `balda22` tampoco -- comparte clave_excel con
 * `balda14`, que es la primaria (ver `ocupacion.ts::esZonaPrimariaParaSuClave`). */
export const ZONAS_V3: { nombreSvg: string; zonaId: string; claveExcel: string | null }[] = [
  { nombreSvg: 'Rack Doble', zonaId: 'doble', claveExcel: null },
  { nombreSvg: 'Rack Simple', zonaId: 'simple', claveExcel: '5. RACK SIMPLE' },
  { nombreSvg: 'Rack Balda 2.2', zonaId: 'balda22', claveExcel: null },
  { nombreSvg: 'Rack Balda 1.4', zonaId: 'balda14', claveExcel: '4. RACK BALDA' },
  { nombreSvg: 'Estanteria Multinivel', zonaId: 'estanteria', claveExcel: '7. MEZANNINE' },
];
