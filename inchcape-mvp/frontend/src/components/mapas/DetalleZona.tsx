import { useEffect, useMemo, useState } from 'react';
import type { RecomendacionSKU } from '../../api/pipeline';
import {
  actualizarRegla,
  crearRegla,
  eliminarRegla,
  fetchReglas,
  nuevoIdRegla,
  type Operador,
  type Regla,
  type ReglaAtributoDef,
  type ReglaIncompatibilidadDef,
} from '../../api/reglas';
import { ApiError } from '../../api/config';
import type { Zona } from '../../api/zonas';
import { esZonaPrimariaParaSuClave } from './ocupacion';
import { GrillaSkus, type EstadoSlot, type ModoColorGrilla } from './GrillaSkus';
import './DetalleZona.css';

const OPERADORES: Operador[] = ['>', '>=', '<', '<=', '==', '!='];
const CAMPOS_ATRIBUTO = ['PESO_KG', 'VOLUMEN_M3', 'ABC', 'FAMILIA'];

function cumpleCondicion(valorSku: string | number, operador: Operador, valor: string | number): boolean {
  if (typeof valor === 'number') {
    const a = Number(valorSku);
    switch (operador) {
      case '==': return a === valor;
      case '!=': return a !== valor;
      case '>': return a > valor;
      case '>=': return a >= valor;
      case '<': return a < valor;
      case '<=': return a <= valor;
    }
  }
  const a = String(valorSku);
  return operador === '!=' ? a !== valor : a === valor;
}

/** SKU que hoy están en esta zona y quedarían en conflicto si la regla propuesta se guardara activa. */
function skusAfectados(
  recomendaciones: RecomendacionSKU[],
  zona: Zona,
  def: ReglaAtributoDef,
): RecomendacionSKU[] {
  // Zona no primaria de su clave_excel (ver esZonaPrimariaParaSuClave) ->
  // ningún SKU real se considera "presente" aquí, nada que afectar.
  if (!esZonaPrimariaParaSuClave(zona)) return [];
  const presentesHoy = recomendaciones.filter((r) => r.ZONA_ACTUAL === zona.clave_excel);
  return presentesHoy.filter((r) => {
    const valorSku = r[def.campo as keyof RecomendacionSKU] as string | number;
    const cumple = cumpleCondicion(valorSku, def.operador, def.valor);
    // "prohibida": la regla saca de la zona a quien SÍ cumple la condición.
    // "permitida": la regla solo deja quedarse a quien cumple -> afecta a quien NO cumple.
    return def.zona_prohibida ? cumple : !cumple;
  });
}

export function DetalleZona({
  zona,
  recomendaciones,
  onClose,
}: {
  zona: Zona;
  recomendaciones: RecomendacionSKU[];
  onClose: () => void;
}) {
  const { skusHoy, skusPropuesta, entranSet, salenSet } = useMemo(() => {
    // "4. RACK BALDA" y "8. CLUSTER" son clave_excel compartida entre 2
    // geometrías -- si esta zona no es la primaria para su clave, no le
    // corresponde ningún SKU (evita mostrarlo duplicado en ambas).
    const esPrimaria = esZonaPrimariaParaSuClave(zona);
    const hoy = esPrimaria ? recomendaciones.filter((r) => r.ZONA_ACTUAL === zona.clave_excel) : [];
    const propuesta = esPrimaria ? recomendaciones.filter((r) => r.ZONA_RECOMENDADA === zona.clave_excel) : [];
    const hoySet = new Set(hoy.map((r) => r.SKU));
    const propSet = new Set(propuesta.map((r) => r.SKU));
    return {
      skusHoy: hoy,
      skusPropuesta: propuesta,
      entranSet: new Set([...propSet].filter((s) => !hoySet.has(s))),
      salenSet: new Set([...hoySet].filter((s) => !propSet.has(s))),
    };
  }, [zona, recomendaciones]);

  const estadoHoy = (r: RecomendacionSKU): EstadoSlot => (salenSet.has(r.SKU) ? 'sale' : 'normal');
  const estadoPropuesta = (r: RecomendacionSKU): EstadoSlot => (entranSet.has(r.SKU) ? 'entra' : 'normal');

  const [modoColor, setModoColor] = useState<ModoColorGrilla>('movimiento');
  const rangoRotacion = useMemo(() => {
    const valores = recomendaciones.map((r) => r.ROTACION_6M);
    return { min: Math.min(...valores), max: Math.max(...valores) };
  }, [recomendaciones]);

  const [reglas, setReglas] = useState<Regla[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  function cargar() {
    fetchReglas().then(setReglas).catch(() => setReglas([]));
  }
  useEffect(cargar, []);

  const reglasZona = useMemo(() => {
    if (!reglas) return [];
    return reglas.filter((r) => {
      if (r.tipo !== 'atributo') return false;
      const d = r.definicion as ReglaAtributoDef;
      return d.zona_permitida === zona.clave_excel || d.zona_prohibida === zona.clave_excel;
    });
  }, [reglas, zona]);
  const incompatibilidadesActivas = reglas?.filter((r) => r.activa && r.tipo === 'incompatibilidad') ?? [];

  async function alternar(r: Regla) {
    setOcupado(true);
    try {
      await actualizarRegla(r.id, { ...r, activa: !r.activa });
      cargar();
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : 'No se pudo actualizar la regla.');
    } finally {
      setOcupado(false);
    }
  }

  async function borrar(id: string) {
    setOcupado(true);
    try {
      await eliminarRegla(id);
      cargar();
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : 'No se pudo eliminar la regla.');
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div className="detalle-zona-overlay" onClick={onClose}>
      <div className="detalle-zona-panel" onClick={(e) => e.stopPropagation()} role="dialog" aria-label={`Detalle de ${zona.nombre}`}>
        <header className="detalle-zona-header">
          <div>
            <h2>{zona.nombre}</h2>
            <span className="mono detalle-zona-clave">{zona.clave_excel}</span>
          </div>
          <button className="detalle-zona-cerrar" onClick={onClose} aria-label="Cerrar">
            ✕
          </button>
        </header>

        {zona.clave_excel === '—' && (
          <p className="detalle-zona-aviso">
            Esta zona no tiene equivalente en <span className="mono">LAYOUT_CD</span> (Excel) — es una zona
            auxiliar del plano, no participa del slotting de SKU ni admite reglas.
          </p>
        )}

        <div className="detalle-zona-restricciones">
          <h3>Restricciones activas en esta zona</h3>
          {error && <p className="estado-error" style={{ marginBottom: 8 }}>{error}</p>}
          {reglasZona.length === 0 && incompatibilidadesActivas.length === 0 ? (
            <p className="detalle-zona-sin-reglas">Ninguna regla restringe esta zona todavía.</p>
          ) : (
            <ul className="detalle-zona-lista-reglas">
              {reglasZona.map((r) => {
                const d = r.definicion as ReglaAtributoDef;
                return (
                  <li key={r.id} style={{ opacity: r.activa ? 1 : 0.5 }}>
                    <span>
                      <b>{r.nombre}</b> —{' '}
                      <span className="mono">
                        {d.campo} {d.operador} {d.valor}
                      </span>{' '}
                      → {d.zona_permitida ? 'solo estos SKU pueden estar aquí' : 'estos SKU no pueden estar aquí'}
                    </span>
                    <span className="detalle-zona-acciones-regla">
                      <button className="boton boton-secundario" disabled={ocupado} onClick={() => alternar(r)}>
                        {r.activa ? 'Desactivar' : 'Activar'}
                      </button>
                      <button className="boton boton-secundario" disabled={ocupado} onClick={() => borrar(r.id)}>
                        Eliminar
                      </button>
                    </span>
                  </li>
                );
              })}
              {incompatibilidadesActivas.map((r) => {
                const d = r.definicion as ReglaIncompatibilidadDef;
                return (
                  <li key={r.id}>
                    <span>
                      <b>{r.nombre}</b> — <span className="mono">{d.familia_a}</span> y{' '}
                      <span className="mono">{d.familia_b}</span> no comparten zona (aplica a todas las zonas)
                    </span>
                  </li>
                );
              })}
            </ul>
          )}

          {zona.clave_excel !== '—' && (
            <FormularioReglaZona
              zona={zona}
              recomendaciones={recomendaciones}
              setError={setError}
              onCreada={cargar}
            />
          )}
        </div>

        <div className="ctrl" role="group" aria-label="Color de los espacios">
          <button aria-pressed={modoColor === 'movimiento'} onClick={() => setModoColor('movimiento')}>
            Por movimiento
          </button>
          <button aria-pressed={modoColor === 'rotacion'} onClick={() => setModoColor('rotacion')}>
            Por rotación
          </button>
        </div>

        <div className="detalle-zona-columnas">
          <section>
            <h3>
              Hoy <span className="mono">({skusHoy.length} SKU)</span>
            </h3>
            <GrillaSkus
              zonaId={zona.id}
              skus={skusHoy}
              estado={estadoHoy}
              vacioTexto="Ningún SKU está aquí hoy."
              modo={modoColor}
              rangoRotacion={rangoRotacion}
            />
          </section>
          <section>
            <h3>
              Propuesta <span className="mono">({skusPropuesta.length} SKU)</span>
            </h3>
            <GrillaSkus
              zonaId={zona.id}
              skus={skusPropuesta}
              estado={estadoPropuesta}
              vacioTexto="Ningún SKU se recomienda aquí."
              modo={modoColor}
              rangoRotacion={rangoRotacion}
            />
          </section>
        </div>

        <p className="detalle-zona-leyenda">
          <span className="leyenda-item"><i className="leyenda-chip chip-sale" /> se va</span>
          <span className="leyenda-item"><i className="leyenda-chip chip-entra" /> llega</span>
          <span className="leyenda-item"><i className="leyenda-chip chip-normal" /> se mantiene</span>
        </p>
        <p className="detalle-zona-nota">
          La disposición es un orden lógico por SKU, no la posición física real del estante —{' '}
          <span className="mono">STOCK_ACTUAL</span> solo registra un código secuencial de ubicación
          (<span className="mono">UB00001…</span>), sin fila/columna/nivel medidos.
        </p>
      </div>
    </div>
  );
}

function FormularioReglaZona({
  zona,
  recomendaciones,
  setError,
  onCreada,
}: {
  zona: Zona;
  recomendaciones: RecomendacionSKU[];
  setError: (e: string | null) => void;
  onCreada: () => void;
}) {
  const [abierto, setAbierto] = useState(false);
  const [nombre, setNombre] = useState('');
  const [campo, setCampo] = useState('PESO_KG');
  const [operador, setOperador] = useState<Operador>('>=');
  const [valor, setValor] = useState('');
  const [accion, setAccion] = useState<'permitida' | 'prohibida'>('prohibida');
  const [justificacion, setJustificacion] = useState('');
  const [enviando, setEnviando] = useState(false);

  const familias = useMemo(() => [...new Set(recomendaciones.map((r) => r.FAMILIA))].sort(), [recomendaciones]);
  const esNumerico = campo === 'PESO_KG' || campo === 'VOLUMEN_M3';

  const definicionPropuesta: ReglaAtributoDef | null = useMemo(() => {
    if (valor === '') return null;
    return {
      campo,
      operador,
      valor: esNumerico ? Number(valor) : valor,
      zona_permitida: accion === 'permitida' ? zona.clave_excel : null,
      zona_prohibida: accion === 'prohibida' ? zona.clave_excel : null,
    };
  }, [campo, operador, valor, accion, esNumerico, zona]);

  const afectados = useMemo(
    () => (definicionPropuesta ? skusAfectados(recomendaciones, zona, definicionPropuesta) : []),
    [definicionPropuesta, recomendaciones, zona],
  );

  function limpiar() {
    setNombre('');
    setValor('');
    setJustificacion('');
    setAbierto(false);
  }

  async function crear(confirmarImpacto: boolean) {
    if (!nombre.trim() || !definicionPropuesta) return setError('Completa nombre, campo y valor.');
    if (afectados.length > 0 && !confirmarImpacto) return;
    setEnviando(true);
    setError(null);
    try {
      await crearRegla({
        id: nuevoIdRegla(),
        tipo: 'atributo',
        nombre: nombre.trim(),
        definicion: definicionPropuesta,
        activa: true,
        justificacion,
      });
      limpiar();
      onCreada();
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : 'No se pudo crear la regla.');
    } finally {
      setEnviando(false);
    }
  }

  if (!abierto) {
    return (
      <button className="boton boton-secundario detalle-zona-agregar-regla" onClick={() => setAbierto(true)}>
        + Agregar regla a esta zona
      </button>
    );
  }

  return (
    <form
      className="detalle-zona-form-regla"
      onSubmit={(e) => {
        e.preventDefault();
        crear(false);
      }}
    >
      <label className="reglas-campo">
        Nombre
        <input value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Ej. Solo pesados aquí" />
      </label>
      <div className="reglas-fila">
        <label className="reglas-campo">
          Campo
          <select value={campo} onChange={(e) => setCampo(e.target.value)}>
            {CAMPOS_ATRIBUTO.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        <label className="reglas-campo">
          Operador
          <select value={operador} onChange={(e) => setOperador(e.target.value as Operador)}>
            {OPERADORES.map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
        </label>
        <label className="reglas-campo">
          Valor
          {campo === 'ABC' ? (
            <select value={valor} onChange={(e) => setValor(e.target.value)}>
              <option value="">—</option>
              {['A', 'B', 'C'].map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
          ) : campo === 'FAMILIA' && familias.length > 0 ? (
            <select value={valor} onChange={(e) => setValor(e.target.value)}>
              <option value="">—</option>
              {familias.map((f) => <option key={f} value={f}>{f}</option>)}
            </select>
          ) : (
            <input type={esNumerico ? 'number' : 'text'} step="0.01" value={valor} onChange={(e) => setValor(e.target.value)} />
          )}
        </label>
        <label className="reglas-campo">
          Acción
          <select value={accion} onChange={(e) => setAccion(e.target.value as 'permitida' | 'prohibida')}>
            <option value="prohibida">Prohibir en esta zona</option>
            <option value="permitida">Solo permitir en esta zona</option>
          </select>
        </label>
      </div>
      <label className="reglas-campo">
        Justificación
        <input value={justificacion} onChange={(e) => setJustificacion(e.target.value)} placeholder="Opcional" />
      </label>

      {afectados.length > 0 && (
        <div className="detalle-zona-alerta-impacto">
          <p>
            <b>{afectados.length} SKU</b> que están hoy en esta zona quedarían en conflicto con esta regla:
          </p>
          <p className="mono detalle-zona-alerta-lista">
            {afectados.slice(0, 12).map((r) => r.SKU).join(', ')}
            {afectados.length > 12 ? `, +${afectados.length - 12} más` : ''}
          </p>
          <p className="detalle-zona-alerta-nota">
            Guardarla no los mueve solo — el optimizador los reubicará recién cuando vuelvas a ejecutar el pipeline.
          </p>
        </div>
      )}

      <div className="detalle-zona-form-acciones">
        <button type="button" className="boton boton-secundario" onClick={limpiar} disabled={enviando}>
          Cancelar
        </button>
        {afectados.length > 0 ? (
          <button type="button" className="boton" onClick={() => crear(true)} disabled={enviando}>
            {enviando ? 'Guardando…' : `Crear de todas formas (${afectados.length} afectados)`}
          </button>
        ) : (
          <button type="submit" className="boton" disabled={enviando}>
            {enviando ? 'Guardando…' : 'Crear regla'}
          </button>
        )}
      </div>
    </form>
  );
}
