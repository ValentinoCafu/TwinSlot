import { useEffect, useMemo, useState } from 'react';
import { useZonas } from '../api/zonas';
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
  type ReglaUmbralDef,
  type TipoRegla,
} from '../api/reglas';
import { ApiError } from '../api/config';
import { usePipeline } from '../context/PipelineContext';
import './ReglasView.css';

const OPERADORES: Operador[] = ['>', '>=', '<', '<=', '==', '!='];
const CAMPOS_ATRIBUTO = ['PESO_KG', 'VOLUMEN_M3', 'ABC', 'FAMILIA'];

function formatearDefinicion(r: Regla): string {
  if (r.tipo === 'atributo') {
    const d = r.definicion as ReglaAtributoDef;
    const destino = d.zona_permitida ? `forzar a "${d.zona_permitida}"` : `prohibir en "${d.zona_prohibida}"`;
    return `${d.campo} ${d.operador} ${d.valor} → ${destino}`;
  }
  if (r.tipo === 'incompatibilidad') {
    const d = r.definicion as ReglaIncompatibilidadDef;
    return `"${d.familia_a}" no comparte zona con "${d.familia_b}"`;
  }
  const d = r.definicion as ReglaUmbralDef;
  return `${d.campo_evaluado} ${d.operador} ${d.valor_umbral} → ${d.accion}`;
}

export function ReglasView() {
  const { zonas } = useZonas();
  const { resultado } = usePipeline();
  const [reglas, setReglas] = useState<Regla[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  const zonasExcel = useMemo(
    () => [...new Set((zonas ?? []).map((z) => z.clave_excel))].filter((c) => c !== '—' && c !== '(nuevo)').sort(),
    [zonas],
  );
  const familias = useMemo(
    () => [...new Set((resultado?.recomendaciones ?? []).map((r) => r.FAMILIA))].sort(),
    [resultado],
  );

  function cargar() {
    fetchReglas()
      .then(setReglas)
      .catch((e: unknown) => setError(e instanceof ApiError ? e.detail : 'No se pudo conectar con el backend.'));
  }
  useEffect(cargar, []);

  async function alternarActiva(r: Regla) {
    setGuardando(true);
    try {
      await actualizarRegla(r.id, { ...r, activa: !r.activa });
      cargar();
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : 'No se pudo actualizar la regla.');
    } finally {
      setGuardando(false);
    }
  }

  async function borrar(id: string) {
    setGuardando(true);
    try {
      await eliminarRegla(id);
      cargar();
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : 'No se pudo eliminar la regla.');
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div>
      <FormularioRegla zonasExcel={zonasExcel} familias={familias} onCreada={cargar} setError={setError} />

      <section className="panel">
        <header>
          <h2>Reglas activas</h2>
          <span className="note">{reglas?.length ?? 0} reglas</span>
        </header>
        <div className="panel-body">
          {error && <p className="estado-error" style={{ marginBottom: 10 }}>{error}</p>}
          {!reglas ? (
            <p>Cargando…</p>
          ) : reglas.length === 0 ? (
            <p style={{ fontSize: 12.5, color: 'var(--grafito2)' }}>Todavía no hay reglas configuradas.</p>
          ) : (
            <div className="scroll">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Tipo</th>
                    <th>Nombre</th>
                    <th>Definición</th>
                    <th>Justificación</th>
                    <th>Activa</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {reglas.map((r) => (
                    <tr key={r.id} style={{ opacity: r.activa ? 1 : 0.5 }}>
                      <td className="mono" style={{ fontSize: 11 }}>{r.id}</td>
                      <td>{r.tipo}</td>
                      <td>{r.nombre}</td>
                      <td className="mono" style={{ fontSize: 11.5 }}>{formatearDefinicion(r)}</td>
                      <td style={{ fontSize: 11.5, color: 'var(--grafito2)' }}>{r.justificacion}</td>
                      <td>
                        <button className="boton boton-secundario" disabled={guardando} onClick={() => alternarActiva(r)}>
                          {r.activa ? 'Desactivar' : 'Activar'}
                        </button>
                      </td>
                      <td>
                        <button className="boton boton-secundario" disabled={guardando} onClick={() => borrar(r.id)}>
                          Eliminar
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p style={{ fontSize: 11.5, color: 'var(--grafito2)', marginTop: 12 }}>
            Los cambios aquí no recalculan solos — ve a <b>Dashboard</b> o <b>Puntuación</b> y ejecuta el pipeline
            de nuevo para ver el efecto en las recomendaciones.
          </p>
        </div>
      </section>
    </div>
  );
}

function FormularioRegla({
  zonasExcel,
  familias,
  onCreada,
  setError,
}: {
  zonasExcel: string[];
  familias: string[];
  onCreada: () => void;
  setError: (e: string | null) => void;
}) {
  const [tipo, setTipo] = useState<TipoRegla>('atributo');
  const [nombre, setNombre] = useState('');
  const [justificacion, setJustificacion] = useState('');
  const [enviando, setEnviando] = useState(false);

  // atributo
  const [campo, setCampo] = useState('PESO_KG');
  const [operador, setOperador] = useState<Operador>('>=');
  const [valor, setValor] = useState('');
  const [accionZona, setAccionZona] = useState<'permitida' | 'prohibida'>('prohibida');
  const [zonaObjetivo, setZonaObjetivo] = useState('');

  // incompatibilidad
  const [familiaA, setFamiliaA] = useState('');
  const [familiaB, setFamiliaB] = useState('');

  // umbral
  const [campoUmbral, setCampoUmbral] = useState('PAYBACK_ESTIMADO');
  const [operadorUmbral, setOperadorUmbral] = useState<Operador>('<=');
  const [valorUmbral, setValorUmbral] = useState('');
  const [accionUmbral, setAccionUmbral] = useState('no mover');

  const esNumerico = campo === 'PESO_KG' || campo === 'VOLUMEN_M3';

  function limpiar() {
    setNombre('');
    setJustificacion('');
    setValor('');
    setZonaObjetivo('');
    setFamiliaA('');
    setFamiliaB('');
    setValorUmbral('');
  }

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    if (!nombre.trim()) return setError('La regla necesita un nombre.');

    let definicion: ReglaAtributoDef | ReglaIncompatibilidadDef | ReglaUmbralDef;
    if (tipo === 'atributo') {
      if (!zonaObjetivo || valor === '') return setError('Completa campo, valor y zona.');
      definicion = {
        campo,
        operador,
        valor: esNumerico ? Number(valor) : valor,
        zona_permitida: accionZona === 'permitida' ? zonaObjetivo : null,
        zona_prohibida: accionZona === 'prohibida' ? zonaObjetivo : null,
      };
    } else if (tipo === 'incompatibilidad') {
      if (!familiaA || !familiaB) return setError('Completa las dos familias.');
      definicion = { familia_a: familiaA, familia_b: familiaB, modo: 'misma_zona_prohibida' };
    } else {
      if (valorUmbral === '') return setError('Completa el valor del umbral.');
      definicion = { campo_evaluado: campoUmbral, operador: operadorUmbral, valor_umbral: Number(valorUmbral), accion: accionUmbral };
    }

    setEnviando(true);
    setError(null);
    try {
      await crearRegla({ id: nuevoIdRegla(), tipo, nombre: nombre.trim(), definicion, activa: true, justificacion });
      limpiar();
      onCreada();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'No se pudo crear la regla.');
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section className="panel">
      <header>
        <h2>Nueva regla</h2>
        <span className="note">Restricción dura sobre el optimizador</span>
      </header>
      <form className="panel-body reglas-form" onSubmit={enviar}>
        <div className="ctrl" role="group" aria-label="Tipo de regla">
          {(['atributo', 'incompatibilidad', 'umbral'] as const).map((t) => (
            <button key={t} type="button" aria-pressed={tipo === t} onClick={() => setTipo(t)}>
              {t}
            </button>
          ))}
        </div>

        <label className="reglas-campo">
          Nombre
          <input value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Ej. Piso solo para SKU pesados" />
        </label>

        {tipo === 'atributo' && (
          <div className="reglas-fila">
            <label className="reglas-campo">
              Campo
              <select value={campo} onChange={(e) => setCampo(e.target.value)}>
                {CAMPOS_ATRIBUTO.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </label>
            <label className="reglas-campo">
              Operador
              <select value={operador} onChange={(e) => setOperador(e.target.value as Operador)}>
                {OPERADORES.map((o) => (
                  <option key={o} value={o}>{o}</option>
                ))}
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
              <select value={accionZona} onChange={(e) => setAccionZona(e.target.value as 'permitida' | 'prohibida')}>
                <option value="prohibida">Prohibir en zona</option>
                <option value="permitida">Forzar a zona</option>
              </select>
            </label>
            <label className="reglas-campo">
              Zona
              <select value={zonaObjetivo} onChange={(e) => setZonaObjetivo(e.target.value)}>
                <option value="">—</option>
                {zonasExcel.map((z) => <option key={z} value={z}>{z}</option>)}
              </select>
            </label>
          </div>
        )}

        {tipo === 'incompatibilidad' && (
          <div className="reglas-fila">
            <label className="reglas-campo">
              Familia A
              {familias.length > 0 ? (
                <select value={familiaA} onChange={(e) => setFamiliaA(e.target.value)}>
                  <option value="">—</option>
                  {familias.map((f) => <option key={f} value={f}>{f}</option>)}
                </select>
              ) : (
                <input value={familiaA} onChange={(e) => setFamiliaA(e.target.value)} />
              )}
            </label>
            <label className="reglas-campo">
              Familia B
              {familias.length > 0 ? (
                <select value={familiaB} onChange={(e) => setFamiliaB(e.target.value)}>
                  <option value="">—</option>
                  {familias.map((f) => <option key={f} value={f}>{f}</option>)}
                </select>
              ) : (
                <input value={familiaB} onChange={(e) => setFamiliaB(e.target.value)} />
              )}
            </label>
            <p className="reglas-nota">No comparten zona (modo binario — distancia mínima en metros pendiente de geometría confirmada).</p>
          </div>
        )}

        {tipo === 'umbral' && (
          <div className="reglas-fila">
            <label className="reglas-campo">
              Campo evaluado
              <input value={campoUmbral} onChange={(e) => setCampoUmbral(e.target.value)} />
            </label>
            <label className="reglas-campo">
              Operador
              <select value={operadorUmbral} onChange={(e) => setOperadorUmbral(e.target.value as Operador)}>
                {OPERADORES.map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
            </label>
            <label className="reglas-campo">
              Valor umbral
              <input type="number" step="0.01" value={valorUmbral} onChange={(e) => setValorUmbral(e.target.value)} />
            </label>
            <label className="reglas-campo">
              Acción
              <input value={accionUmbral} onChange={(e) => setAccionUmbral(e.target.value)} />
            </label>
            <p className="reglas-nota">
              Todavía no conectada al pipeline (requiere <span className="mono">PAYBACK_ESTIMADO</span> real, ver
              `FEATURES-Y-KPIS.md`) — queda guardada, lista para cuando exista ese dato.
            </p>
          </div>
        )}

        <label className="reglas-campo">
          Justificación
          <input value={justificacion} onChange={(e) => setJustificacion(e.target.value)} placeholder="Opcional" />
        </label>

        <button className="boton" type="submit" disabled={enviando}>
          {enviando ? 'Guardando…' : 'Crear regla'}
        </button>
      </form>
    </section>
  );
}
