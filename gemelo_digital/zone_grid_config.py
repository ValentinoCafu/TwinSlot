from dataclasses import dataclass, field
from typing import Literal

TipoOperacion = Literal["Picker", "Reach", "Grua", "Mixto", "Estatico"]


@dataclass
class SubZona:
    nombre: str
    n_pasillos: int
    n_ubicaciones: int
    operacion: TipoOperacion
    # niveles verticales: por defecto 4 para Picker, 6 para Reach/Grua
    n_niveles: int = field(default=0)

    def __post_init__(self):
        if self.n_niveles == 0:
            self.n_niveles = 6 if self.operacion in ("Reach", "Grua") else 4

    @property
    def ubicaciones_por_pasillo(self) -> float:
        return round(self.n_ubicaciones / self.n_pasillos, 1)

    def nivel_requiere_grua(self, nivel: int) -> bool:
        """Nivel 1 = piso. A partir del nivel 2 en zonas Reach/Mixto se
        considera que se necesita grúa (regla planteada por el compañero)."""
        return self.operacion in ("Reach", "Grua", "Mixto") and nivel >= 2


# ---------------------------------------------------------------------------
# MAPEO: zona del Excel -> lista de sub-zonas reales del plano
# ---------------------------------------------------------------------------
ZONE_GRID_CONFIG: dict[str, list[SubZona]] = {
    "8. CLUSTER": [
        SubZona("Cluster 1", n_pasillos=3, n_ubicaciones=3743, operacion="Picker"),
        SubZona("Cluster 2", n_pasillos=3, n_ubicaciones=5182, operacion="Picker"),
        SubZona("Cluster 3", n_pasillos=3, n_ubicaciones=1711, operacion="Picker"),
    ],
    "7. MEZANNINE": [
        SubZona("Alto Valor", n_pasillos=1, n_ubicaciones=66, operacion="Picker"),
        SubZona("Estantería 1", n_pasillos=10, n_ubicaciones=506, operacion="Picker"),
        SubZona("Estantería 2", n_pasillos=10, n_ubicaciones=516, operacion="Picker"),
        SubZona("Estantería 3", n_pasillos=10, n_ubicaciones=540, operacion="Picker"),
    ],
    # 4. RACK BALDA comparte el mismo pool físico "Multinivel Estantería"
    # que 7. MEZANNINE (ver imagen 3: "Antes: Mezanine / Ahora: Multinivel
    # Estantería" mapea ambos). Se referencia la misma lista de sub-zonas.
    "4. RACK BALDA": [
        SubZona("Estantería 1", n_pasillos=10, n_ubicaciones=506, operacion="Picker"),
        SubZona("Estantería 2", n_pasillos=10, n_ubicaciones=516, operacion="Picker"),
        SubZona("Estantería 3", n_pasillos=10, n_ubicaciones=540, operacion="Picker"),
    ],
    "5. RACK SIMPLE": [
        SubZona("Rack Doble", n_pasillos=1, n_ubicaciones=265, operacion="Reach"),
        SubZona("Rack Alta Rotación", n_pasillos=2, n_ubicaciones=762, operacion="Picker"),
        SubZona("Rack Pallet", n_pasillos=4, n_ubicaciones=1706, operacion="Reach"),
    ],
    # --- Sin desglose de pasillos/ubicaciones todavía: placeholder 1:1 ---
    "10. UBICACIÓN RECIBO": [  # TODO: confirmar pasillos reales
        SubZona("Recepción de Aéreos", n_pasillos=1, n_ubicaciones=1, operacion="Estatico"),
    ],
    "14. LATERALES": [  # TODO: confirmar pasillos reales
        SubZona("Mesas de Trabajo / Laterales", n_pasillos=1, n_ubicaciones=1, operacion="Estatico"),
    ],
    "2. PISO": [  # TODO: confirmar pasillos reales
        SubZona("Bulk / Piso", n_pasillos=1, n_ubicaciones=1, operacion="Grua"),
    ],
    "1. LLANTAS": [  # TODO: confirmar pasillos reales
        SubZona("Rack Neumáticos", n_pasillos=1, n_ubicaciones=1, operacion="Grua"),
    ],
    "6. RACK COLGANTES": [  # TODO: confirmar pasillos reales
        SubZona("Rack Colgantes", n_pasillos=1, n_ubicaciones=1, operacion="Picker"),
    ],
}


def get_subzonas(zona_excel: str) -> list[SubZona]:
    if zona_excel not in ZONE_GRID_CONFIG:
        raise KeyError(f"Zona '{zona_excel}' no está mapeada en ZONE_GRID_CONFIG.")
    return ZONE_GRID_CONFIG[zona_excel]


if __name__ == "__main__":
    # Prueba rápida: listar el grid resultante para cada zona del Excel
    for zona, subzonas in ZONE_GRID_CONFIG.items():
        print(f"\n{zona}")
        for sz in subzonas:
            print(
                f"  - {sz.nombre}: {sz.n_pasillos} pasillos x "
                f"{sz.ubicaciones_por_pasillo} ubic/pasillo x {sz.n_niveles} niveles "
                f"[{sz.operacion}]"
            )
