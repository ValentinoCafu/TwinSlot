# Features y KPIs del proyecto — Reslotting CD Aldeas

Fecha: 2026-08-23. Consolida el análisis de aterrizaje de datos (KPIs declarados vs. verificados) y el mapa de qué feature del MVP calcula/muestra cada uno. No repite el detalle de arquitectura ya cubierto en `backend/README.md` — lo referencia.

---

## 1. Principio metodológico (léase antes que las tablas)

Toda cifra de este documento está marcada como **declarada** (viene escrita en el Excel del caso, sin fórmula) o **verificada** (se recalculó desde `PEDIDOS ACTUAL`/`LAYOUT_CD` y se muestra cómo). Cuando una cifra declarada no reconcilia con el dato crudo, **se usa la verificada y se deja constancia de la discrepancia** — nunca se oculta ni se fuerza a que cierre. Mismo principio que ya rige el resto del proyecto (`CLAUDE_1.md`, "Nunca inventar cifras: verificar contra los datos").

---

## 2. KPI 1 — Tiempo promedio por pedido

### 2.1 Dónde vive y cómo se declaró

Hoja `RESUMEN`, celda `B4`: el valor `'12.64 min/pedido'` es **texto tecleado**, no una fórmula — verificado abriendo el workbook con `openpyxl` en modo fórmulas (`data_only=False`): la celda no referencia ninguna otra hoja ni celda.

| Métrica | Actual (declarado) | Meta | Mejora requerida |
|---|---|---|---|
| Tiempo promedio | 12.64 min/pedido | 9.48 min/pedido | −25% |

Nota interna: 12.64 × 0.75 = 9.48 exacto — la meta es consistente *dentro* de la hoja `RESUMEN` (es el 75% del "actual"), pero eso no dice nada sobre si el 12.64 original tiene respaldo en los datos transaccionales.

### 2.2 Cálculo verificado desde los datos crudos

Fuente: `PEDIDOS ACTUAL` (1500 líneas, 435 pedidos distintos), columna `TIEMPO_HOY_MIN`.

**Definición operativa:** tiempo total que le toma a un operario completar un pedido = suma de `TIEMPO_HOY_MIN` de todas sus líneas (no el promedio de sus líneas — un picker suma sus recorridos, no los promedia). Luego se promedia esa suma entre los 435 pedidos.

$$\text{tiempo\_promedio\_pedido} = \frac{\sum_{\text{las 1500 líneas}} \text{TIEMPO\_HOY\_MIN}}{\text{n.º de pedidos distintos (435)}} = \frac{6{,}806.92}{435} = \mathbf{15.65 \text{ min/pedido}}$$

```python
pedidos['TIEMPO_HOY_MIN'].sum() / pedidos['PEDIDO_ID'].nunique()   # 15.6481
```

**Ejemplo trazado (pedido 1000):** 3 líneas (SKU00093 en 1. LLANTAS, SKU00032 en 2. PISO, SKU00007 en 1. LLANTAS) → 8.37 + 1.67 + 8.37 = **18.41 min** para completar ese pedido específico; ese valor es uno de los 435 que entran al promedio.

**Error de método frecuente (ya descartado en el camino):** promediar `TIEMPO_HOY_MIN` *dentro* de cada pedido antes de promediar entre pedidos da 4.54 min/pedido — es el promedio por *línea*, no por *pedido* (subestima el trabajo real: 4.54 × 435 = 1,975 min totales, contra los 6,806.92 min reales).

**Mecánica de `TIEMPO_HOY_MIN`:** es determinista de la zona, no del SKU — `TIEMPO_HOY_MIN = TIEMPO_MINUTOS (de LAYOUT_CD) × 1.0417` (ratio confirmado ≈1.0419 en las 8 zonas que sí aparecen en pedidos; "14. LATERALES" no aparece en ninguna línea — hoy no se pica nada desde ahí). No hay componente de tiempo intrínseco al SKU en este dataset (ya documentado en `CLAUDE_1.md` #1).

### 2.3 Veredicto

| | Valor | Fuente |
|---|---|---|
| Declarado | 12.64 min/pedido | Texto en `RESUMEN!B4`, sin fórmula, no reconcilia con ningún cálculo posible sobre `PEDIDOS ACTUAL` |
| **Verificado (usar este)** | **15.65 min/pedido** | `Σ TIEMPO_HOY_MIN / n_pedidos`, reproducible por cualquiera con el Excel |
| Meta declarada | 9.48 min/pedido | Consistente como 75% del declarado, no como 75% del verificado |

---

## 3. KPI 2 — Productividad

### 3.1 Dónde vive y cómo se declaró

Hoja `RESUMEN`, celda `B5`: `'11.64 SKU/HH'`, mismo caso — texto sin fórmula.

| Métrica | Actual (declarado) | Meta | Mejora requerida |
|---|---|---|---|
| Productividad | 11.64 SKU/HH | 13.39 SKU/HH | +15% |

Nota interna: 11.64 × 1.15 = 13.386 ≈ 13.39 — de nuevo, consistente *dentro* de la hoja, no contra `PEDIDOS ACTUAL`.

### 3.2 Cálculo verificado desde los datos crudos

**Definición operativa:** líneas de pedido completadas por cada hora de trabajo invertida. "Hora-hombre" (HH) aquí **no viene de una planilla de turnos** (esa columna no existe en el dataset) — se deriva del mismo tiempo total de picking, convertido de minutos a horas.

$$\text{HH} = \frac{\sum \text{TIEMPO\_HOY\_MIN}}{60} = \frac{6{,}806.92}{60} = 113.45 \text{ horas}$$

$$\text{Productividad} = \frac{\text{n.º de líneas completadas (1500)}}{\text{HH (113.45)}} = \mathbf{13.22 \text{ líneas/HH}}$$

```python
horas_hombre = pedidos['TIEMPO_HOY_MIN'].sum() / 60   # 113.4487
productividad = len(pedidos) / horas_hombre            # 13.2218
```

**Contraste de fórmulas (para no cruzarlas, como pasó en el análisis):**

| | Tiempo promedio | Productividad |
|---|---|---|
| Numerador | Σ TIEMPO_HOY_MIN (minutos) = 6,806.92 | N.º de líneas = 1,500 |
| Denominador | N.º de **pedidos** = 435 | Σ TIEMPO_HOY_MIN **en horas** = 113.45 |
| Pregunta que responde | "¿Cuántos minutos cuesta UN pedido?" | "¿Cuántas líneas saco POR HORA trabajada?" |
| Resultado | 15.65 min/pedido | 13.22 líneas/HH |

Se comprobó por descarte que ninguna otra combinación razonable (unidades totales de `CANTIDAD`, número de pedidos, sobre esas mismas 113.45 horas) reproduce el 11.64 declarado; el cálculo inverso (¿qué horas-hombre harían falta para que 1500 líneas dieran 11.64?) exige 128.87 horas, no las 113.45 que sí están sustentadas en `TIEMPO_HOY_MIN`.

### 3.3 Veredicto

| | Valor | Fuente |
|---|---|---|
| Declarado | 11.64 SKU/HH | Texto en `RESUMEN!B5`, sin fórmula, no reconcilia con `PEDIDOS ACTUAL` bajo ninguna combinación probada |
| **Verificado (usar este)** | **13.22 líneas/HH** | `n_líneas / (Σ TIEMPO_HOY_MIN / 60)`, reproducible |
| Meta declarada | 13.39 SKU/HH | Consistente como 115% del declarado, no como 115% del verificado |

---

## 4. Tabla resumen (para citar en la presentación)

| KPI | Declarado (Excel, sin fórmula) | Verificado (recalculado desde datos crudos) | Meta declarada |
|---|---|---|---|
| Tiempo promedio | 12.64 min/pedido | **15.65 min/pedido** | 9.48 min/pedido (−25% del declarado) |
| Productividad | 11.64 SKU/HH | **13.22 líneas/HH** | 13.39 SKU/HH (+15% del declarado) |

**Consecuencia para el proyecto:** cualquier "% de mejora" que se presente debe calcularse contra la línea base **verificada** (15.65 / 13.22), no contra la declarada — si el pipeline logra bajar a 9.48 min/pedido, la mejora real respecto al dato defendible es mayor al 25% anunciado, no igual. Esto ya es exactamente lo que hace `dominio/kpis.py` del backend: calcula `tiempo_actual_min`/`reduccion_porcentaje` desde `PEDIDOS ACTUAL` real de cada lote, nunca desde una cifra pegada en un Excel.

---

## 5. Glosario de términos del caso (fuente: hoja `GLOSARIO_GUÍA`)

| Término | Definición (tal cual el caso) | Nombre real de columna en el dataset |
|---|---|---|
| SKU | Stock Keeping Unit — código único del producto | `SKU` |
| ROTACIÓN | Cantidad de veces que se despacha en 6 meses | `ROTACION_6M` — **no usar como proxy de velocidad real**, no correlaciona con hits reales (Pearson 0.028, `CLAUDE_1.md` #2); usar `N_LINEAS` (hits reales de `PEDIDOS ACTUAL`) |
| ABC | A = alta rotación, B = media, C = baja | `ABC` |
| VOL_M3 | Volumen en metros cúbicos | `VOLUMEN_M3` |
| ZONA | Área física del almacén | `ZONA` / `ZONA_ACTUAL` (nombres del Excel — 9 zonas, distintas de las 13 zonas geométricas del plano vectorial, ver `backend/README.md` §3.1) |
| TIEMPO | Minutos que demora buscar y recoger | `TIEMPO_HOY_MIN` (por línea) / `TIEMPO_MINUTOS` (por zona, en `LAYOUT_CD`) |
| CAPACIDAD | Volumen máximo que cabe en la zona | `CAPACIDAD_M3_MAX` / `CAPACIDAD_MAX_M3` |

---

## 6. Features del MVP, mapeadas a estos KPIs

Detalle completo de arquitectura y endpoints en `backend/README.md`; esta tabla es solo el mapa "feature → qué KPI/pregunta de negocio resuelve → dónde se ve".

| Feature | Resuelve | Dónde se ve en el frontend | Endpoint backend |
|---|---|---|---|
| Ingesta validada | Que el tiempo/productividad se calculen siempre desde datos verificados, no pegados a mano | — (hoy solo vía backend, sin UI de carga) | `POST /ingesta` |
| Dashboard de KPIs | Tiempo actual vs. optimizado, ahorro, % SKU movidos (línea base **verificada**, no declarada) | Vista *Dashboard* | `POST /pipeline/ejecutar` → `kpis` |
| Score ponderado + optimización | Reasignar SKU a zonas mejores dentro de restricciones reales | Vista *SKU · slotting*, *Puntuación* | `POST /pipeline/ejecutar` → `recomendaciones` |
| Explicabilidad por SKU | Por qué el score cambia (o no) la zona recomendada de un SKU | Vista *Puntuación* → inspector individual | `GET /recomendaciones/{sku}` |
| Mapas Hoy/Propuesta | Visualizar dónde están los SKU hoy vs. dónde los movería el modelo | Vista *Mapas* | `GET /zonas` + `recomendaciones` |
| Banda de oro NIOSH | Restricción ergonómica de peso/altura, independiente del tiempo/productividad | — (endpoint listo, sin vista dedicada aún) | `GET /ergonomia` |
| Motor de reglas | Restricciones duras de negocio (atributo/incompatibilidad) sobre el optimizador | — (CRUD backend listo, sin tabla editable en frontend aún) | `GET/POST/PUT/DELETE /reglas` |
| Motor de afinidad | Verifica si hay señal real de co-ocurrencia SKU-SKU antes de usarla | — (endpoint listo, sin vista dedicada aún) | `GET /afinidad` |

---

## 7. Pendientes de este mismo ejercicio de aterrizaje

- Las 7 filas restantes de `GLOSARIO_GUÍA`/`RESUMEN` que no se auditaron todavía con este nivel de detalle (si las hay más allá de las 2 ya cubiertas) — repetir el mismo método (buscar la celda, ver si es fórmula o texto, intentar reconstruir desde datos crudos, declarar el veredicto).
- Ninguna de las dos cifras declaradas (12.64, 11.64) tiene una fórmula recuperable dentro del propio workbook — si en algún momento se consigue el reporte operativo real de Inchcape del que probablemente salieron, vale la pena reconciliar contra eso en vez de descartarlas sin más contexto.
