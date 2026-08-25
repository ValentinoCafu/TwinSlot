
from dataclasses import dataclass
from zone_grid_config import ZONE_GRID_CONFIG, SubZona

# Multiplicador de tiempo de picking cuando una posición requiere grúa
# (nivel >= 2 en zonas Reach/Mixto). Valor placeholder -> ajustar con
# datos reales de operación cuando estén disponibles.
MULTIPLICADOR_TIEMPO_GRUA = 1.4


@dataclass
class SlotAssignment:
    sku: str
    zona_excel: str
    subzona: str
    pasillo: int          # eje x
    posicion: int         # eje y
    nivel: int             # eje z
    operacion: str
    requiere_grua: bool
    multiplicador_tiempo: float


class ZoneAssigner:
    """Mantiene el estado de cuántos SKU se han colocado en cada sub-zona
    para poder repartir proporcionalmente los siguientes."""

    def __init__(self):
        # contador de asignados por (zona_excel, nombre_subzona)
        self._asignados: dict[tuple[str, str], int] = {}

    def _elegir_subzona(self, zona_excel: str) -> SubZona:
        subzonas = ZONE_GRID_CONFIG[zona_excel]
        mejor = None
        mejor_ratio = None
        for sz in subzonas:
            asignados = self._asignados.get((zona_excel, sz.nombre), 0)
            # peso = n_ubicaciones de la subzona (capacidad relativa)
            ratio = (asignados + 1) / sz.n_ubicaciones
            if mejor_ratio is None or ratio < mejor_ratio:
                mejor_ratio = ratio
                mejor = sz
        return mejor

    def asignar(self, sku: str, zona_excel: str) -> SlotAssignment:
        if zona_excel not in ZONE_GRID_CONFIG:
            raise KeyError(f"Zona '{zona_excel}' no está en ZONE_GRID_CONFIG.")

        subzona = self._elegir_subzona(zona_excel)
        key = (zona_excel, subzona.nombre)
        idx = self._asignados.get(key, 0)
        self._asignados[key] = idx + 1

        # Llenado del grid: recorre pasillo -> posición -> nivel
        ubic_por_pasillo = max(1, int(subzona.ubicaciones_por_pasillo))
        pasillo = idx % subzona.n_pasillos
        posicion = (idx // subzona.n_pasillos) % ubic_por_pasillo
        nivel = (idx // (subzona.n_pasillos * ubic_por_pasillo)) % subzona.n_niveles + 1

        requiere_grua = subzona.nivel_requiere_grua(nivel)
        multiplicador = MULTIPLICADOR_TIEMPO_GRUA if requiere_grua else 1.0

        return SlotAssignment(
            sku=sku,
            zona_excel=zona_excel,
            subzona=subzona.nombre,
            pasillo=pasillo,
            posicion=posicion,
            nivel=nivel,
            operacion=subzona.operacion,
            requiere_grua=requiere_grua,
            multiplicador_tiempo=multiplicador,
        )

    def resumen(self) -> dict[tuple[str, str], int]:
        """Cuántos SKU quedaron en cada sub-zona (para verificar que el
        reparto respeta las proporciones de n_ubicaciones)."""
        return dict(self._asignados)


def asignar_dataframe(df, col_sku: str, col_zona: str) -> "list[SlotAssignment]":
    """Aplica el reparto a un DataFrame de pandas (ej. ANALYTICS_BASE o el
    output del optimizador con columnas SKU y ZONA_NUEVA)."""
    assigner = ZoneAssigner()
    resultados = []
    for _, row in df.iterrows():
        resultados.append(assigner.asignar(row[col_sku], row[col_zona]))
    return resultados


if __name__ == "__main__":
    # --- Prueba con la distribución real de 100 SKU (ZONA ACTUAL) ---
    from collections import Counter

    distribucion_real = {
        "2. PISO": 27, "1. LLANTAS": 15, "5. RACK SIMPLE": 15,
        "4. RACK BALDA": 12, "7. MEZANNINE": 10, "10. UBICACIÓN RECIBO": 8,
        "8. CLUSTER": 7, "6. RACK COLGANTES": 6,
    }

    assigner = ZoneAssigner()
    resultados = []
    i = 0
    for zona, cantidad in distribucion_real.items():
        for _ in range(cantidad):
            i += 1
            resultados.append(assigner.asignar(f"SKU{i:05d}", zona))

    print(f"Total SKU asignados: {len(resultados)}\n")

    print("Ejemplo de asignaciones (primeras 8):")
    for r in resultados[:8]:
        print(f"  {r.sku} -> {r.zona_excel} / {r.subzona} "
              f"[pasillo={r.pasillo}, pos={r.posicion}, nivel={r.nivel}] "
              f"grua={r.requiere_grua} x{r.multiplicador_tiempo}")

    print("\nReparto resultante por sub-zona (verificar proporcionalidad):")
    for (zona, subzona), n in assigner.resumen().items():
        print(f"  {zona} / {subzona}: {n} SKU")
