# Layout SVG v3 — cómo aprovechar el trazado real del almacén

Fecha: 2026-08-27. Documenta `layout  inchape v3.svg` (raíz del proyecto): qué es, qué contrato debe cumplir para que el resto del pipeline lo entienda, cómo regenerar los datos cuando subas una versión más completa, y dónde se usa hoy.

---

## 1. Qué es el archivo

Fue exportado de una herramienta tipo SCADA/sinóptico ("Synoptic Designer", `data-synoptic-designer-version="2.0.5"` en el `<svg>` raíz). Tiene dos capas:

1. **Capa de fondo**: una imagen trazada (`<image href="data:image/webp;base64,...">`), probablemente el plano/foto real usado como referencia para dibujar encima. Pesa la mayor parte del archivo (~800 KB) y no se usa para nada en el frontend — es solo la guía visual que usaste en el editor.
2. **Capa vectorial** (la que sí importa): grupos `<g id="Grupo_x20_<Nombre de Zona>">`, cada uno con:
   - Un `<path>` con `title="<Nombre de Zona>"` — es el **polígono real del borde de la zona**.
   - Varios `<rect>` — cada uno es **una posición de espacio real**, con su `x`, `y`, `width`, `height` y (si el editor lo generó así) un `transform` de `translate`/`matrix`/`scale`/`rotate` para ubicarlo dentro del polígono.

`_x20_` es el espacio codificado como en una URL — así nombra los ids el editor cuando el nombre de la zona tiene espacios.

## 2. Contrato para que el script lo reconozca

`scripts/extraer_layout_svg.py` busca exactamente esto — si sigues dibujando zonas nuevas en el mismo editor con la misma convención, el script las levanta solas, sin tocar código:

- Un `<g id="Grupo_x20_...">` por zona.
- Dentro, **un** `<path>` con atributo `title` = el nombre de la zona (así queda etiquetada).
- Dentro, **uno o más** `<rect>` por cada posición de espacio real que quieras que cuente como una ubicación.

No importa el orden interno de los `<rect>`, ni si tienen `transform` o no — el script resuelve `translate`, `matrix`, `scale` y `rotate` a coordenadas finales absolutas. Si algún rect queda con rotación o escala no-axial (una forma que ya no es un rectángulo recto en pantalla), el script lo avisa por consola (no lo descarta, pero su `x/y/width/height` extraído es solo el bounding box, no la forma exacta).

## 3. Estado actual (v3, ago 2026)

| Zona trazada | Espacios en el SVG | Total ya definido en `espaciosZona.ts` (tu Excel) |
|---|---|---|
| Rack Doble | 36 | 50 |
| Rack Simple | 35 | 84 |
| Rack Balda 2.2 | 39 | 162 |
| Rack Balda 1.4 (`title="Balda 1.4"`) | 39 | 96 |
| Estantería Multinivel | 278 | 211 |

**Faltan de trazar:** Bulk, Cluster Multinivel, Rack Neumáticos (Llantas), Rack Colgantes, Recepción de aéreos, Mesas de trabajo, Zona de carpintería.

Los conteos de este SVG **no coinciden todavía** con los que ya confirmaste por Excel — es un trazado en progreso, no la versión final. Por decisión explícita (ago 2026), mientras tanto:
- El **plano/forma** de estas 5 zonas se usa tal cual, en una vista previa aparte.
- La **capacidad oficial de espacios** (para "ocupados/libres" en el modal de zona y el mapa principal) sigue siendo la de `espaciosZona.ts`, no la de este SVG.

## 4. Cómo regenerar los datos cuando subas una versión nueva

Desde `MVP-Inchape/`, con el entorno `IngenieriaPython` activo:

```
conda run -n IngenieriaPython python scripts/extraer_layout_svg.py "<nombre del nuevo svg>.svg" frontend/src/data/layoutV3.json
```

Sobrescribe `frontend/src/data/layoutV3.json` — el frontend lo recoge automáticamente (Vite recompila solo). No hace falta tocar `layoutV3.ts` ni `PlanoV3Preview.tsx` **salvo que agregues una zona con un nombre nuevo** — en ese caso, agrégala al array `ZONAS_V3` en `frontend/src/components/mapas/layoutV3.ts` con su `zonaId` (el id que ya usa `zonas.json`/`espaciosZona.ts`) y su `claveExcel` (el nombre real de `LAYOUT_CD`, o `null` si esa zona no tiene equivalente en el Excel — como `Rack Doble` y `Rack Balda 2.2`, que comparten o no tienen `clave_excel`, ver `README.md` del backend §3.1).

## 5. Versión limpia del archivo

`layout  inchape v3.svg` original pesa ~780 KB porque trae embebida la imagen de fondo trazada en base64 (capa `data-synoptic-designer-tracing-layer="true"`) — no se usa para nada fuera del editor donde la dibujaste. `scripts/limpiar_layout_svg.py` genera una copia sin esa capa, sin tocar ninguna zona/path/rect real:

```
conda run -n IngenieriaPython python scripts/limpiar_layout_svg.py "layout  inchape v3.svg" "layout-inchape-v3-limpio.svg"
```

Resultado: **782 KB → 156 KB** (verificado: misma extracción exacta, 36/35/39/39/278 espacios). `layout-inchape-v3-limpio.svg` es la que vive en el repo y la que usa `extraer_layout_svg.py` por defecto — sigue editando el archivo **original** (con la imagen de fondo) en Synoptic Designer si necesitas la referencia visual para seguir trazando; solo vuelve a correr este script sobre la nueva exportación antes de regenerar los datos.

## 6. Dónde se usa hoy

- `frontend/src/data/layoutV3.json` — salida cruda del script (no editar a mano).
- `frontend/src/components/mapas/layoutV3.ts` — tipos + mapeo nombre-de-zona-en-el-SVG → `zonaId`/`claveExcel` de la app.
- `frontend/src/components/mapas/PlanoV3Preview.tsx` — el panel "Plano real (v3)": dibuja el polígono real de cada zona trazada y sus espacios reales, con un toggle **Por ocupación / Por rotación** (reutiliza `colorCalor` de `GrillaSkus.tsx`, mismo calor que ya usa el resto de la app). Se renderiza en dos lugares:
  - Sección **Resumen** (dashboard principal), debajo del mapa de calor esquemático existente.
  - Sección **Mapas**, entre el comparativo Hoy/Propuesta y el plano de referencia por técnica de almacenamiento.

Es **una vista previa/comparativo**, no reemplaza el plano principal (`PlanoBase.tsx`/`zonas.json`) todavía — el rediseño completo del mapa sigue pendiente hasta que el trazado cubra las 13 zonas y se reconcilien los conteos con Excel.

## 7. Próximos pasos (cuando el trazado esté completo)

1. Terminar de trazar las 8 zonas restantes con la misma convención.
2. Decidir y reconciliar: ¿la capacidad final de espacios es la de Excel, la del SVG, o se vuelve a contar directamente desde el trazado final? (mismo tipo de decisión que ya se tomó para las 5 zonas actuales).
3. Recién ahí: promover esta geometría real a reemplazar `zonas.json` (`puntos_svg` aproximados) y `espaciosZona.ts` (grilla CSS ilustrativa) en el plano principal — no antes, para no reconstruir dos veces si el trazado todavía cambia.
