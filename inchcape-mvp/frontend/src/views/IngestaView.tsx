import { useEffect, useMemo, useRef, useState } from 'react';
import { read, utils } from 'xlsx';
import { ApiError } from '../api/config';
import { fetchMapeo, subirIngesta, type Mapeo, type RespuestaIngesta } from '../api/ingesta';
import { PipelineChecklist } from '../components/ui/PipelineChecklist';
import { usePipeline } from '../context/PipelineContext';
import './IngestaView.css';

interface PreviaHoja {
  hoja: string;
  encontrada: boolean;
  encabezados: string[];
  filas: unknown[][];
}

type ModoArchivo = 'excel' | 'csv';

function formatearTamano(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

/** Mismo criterio de normalización que `app/ingesta/servicio.py::_slug`
 * -- para que el emparejamiento nombre-de-archivo -> tabla en la
 * previsualización coincida con lo que hará el backend al subirlo. */
function slug(s: string): string {
  return s
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]/g, '');
}

/** Único Excel (.xlsx/.xls) con las 6 hojas, o varios CSV sueltos (uno
 * por tabla) -- si no calza en ninguno de los dos, no es un modo válido. */
function detectarModo(archivos: File[]): ModoArchivo | null {
  if (archivos.length === 1 && /\.(xlsx|xls)$/i.test(archivos[0].name)) return 'excel';
  if (archivos.length > 0 && archivos.every((f) => /\.csv$/i.test(f.name))) return 'csv';
  return null;
}

async function previsualizarExcel(archivo: File, mapeo: Mapeo): Promise<PreviaHoja[]> {
  const buffer = await archivo.arrayBuffer();
  const libro = read(buffer);
  const hojasPedidas = [...new Set(Object.values(mapeo).map((t) => t.hoja))];
  return hojasPedidas.map((hoja) => {
    const hoja_ = libro.Sheets[hoja];
    if (!hoja_) return { hoja, encontrada: false, encabezados: [], filas: [] };
    const filas = utils.sheet_to_json<unknown[]>(hoja_, { header: 1, blankrows: false, defval: '' });
    return { hoja, encontrada: true, encabezados: (filas[0] ?? []).map(String), filas: filas.slice(1, 6) };
  });
}

async function previsualizarCsvs(archivos: File[], mapeo: Mapeo): Promise<PreviaHoja[]> {
  const hojasPedidas = [...new Set(Object.values(mapeo).map((t) => t.hoja))];
  const previas: PreviaHoja[] = [];
  for (const hoja of hojasPedidas) {
    const archivo = archivos.find((f) => slug(f.name.replace(/\.csv$/i, '')) === slug(hoja));
    if (!archivo) {
      previas.push({ hoja, encontrada: false, encabezados: [], filas: [] });
      continue;
    }
    const texto = await archivo.text();
    const libro = read(texto, { type: 'string' });
    const hoja_ = libro.Sheets[libro.SheetNames[0]];
    const filas = utils.sheet_to_json<unknown[]>(hoja_, { header: 1, blankrows: false, defval: '' });
    previas.push({ hoja, encontrada: true, encabezados: (filas[0] ?? []).map(String), filas: filas.slice(1, 6) });
  }
  return previas;
}

export function IngestaView() {
  const [mapeo, setMapeo] = useState<Mapeo | null>(null);
  const [archivos, setArchivos] = useState<File[]>([]);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resultado, setResultado] = useState<RespuestaIngesta | null>(null);
  const [previa, setPrevia] = useState<PreviaHoja[] | null>(null);
  const [errorPrevia, setErrorPrevia] = useState<string | null>(null);
  const [arrastrando, setArrastrando] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const { ejecutar } = usePipeline();

  const modo = detectarModo(archivos);

  useEffect(() => {
    fetchMapeo()
      .then(setMapeo)
      .catch((e: unknown) => setError(e instanceof ApiError ? e.detail : 'No se pudo conectar con el backend.'));
  }, []);

  function editarColumna(tabla: string, canonico: string, origen: string) {
    setMapeo((m) => (m ? { ...m, [tabla]: { ...m[tabla], columnas: { ...m[tabla].columnas, [canonico]: origen } } } : m));
  }

  async function elegirArchivos(lista: FileList | File[] | null) {
    const nuevos = lista ? Array.from(lista) : [];
    setResultado(null);
    setPrevia(null);
    setErrorPrevia(null);
    if (nuevos.length === 0) {
      setArchivos([]);
      setError(null);
      return;
    }
    const modoDetectado = detectarModo(nuevos);
    if (!modoDetectado) {
      setError('Sube un único archivo Excel (.xlsx/.xls), o varios archivos .csv (uno por tabla).');
      return;
    }
    setError(null);
    setArchivos(nuevos);
    if (!mapeo) return;
    try {
      setPrevia(modoDetectado === 'excel' ? await previsualizarExcel(nuevos[0], mapeo) : await previsualizarCsvs(nuevos, mapeo));
    } catch {
      setErrorPrevia('No se pudo leer el/los archivo(s) en el navegador para previsualizar — igual puedes intentar subirlo.');
    }
  }

  function quitarArchivo(indice: number) {
    elegirArchivos(archivos.filter((_, i) => i !== indice));
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setArrastrando(false);
    elegirArchivos(e.dataTransfer.files);
  }

  async function enviar() {
    if (archivos.length === 0 || !mapeo) return;
    setEnviando(true);
    setError(null);
    setResultado(null);
    try {
      const r = await subirIngesta(archivos, mapeo);
      setResultado(r);
      await ejecutar(); // el lote cambió -- refresca el pipeline con el nuevo dato
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : 'No se pudo ingerir el archivo.');
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section className="panel">
      <header>
        <h2>Ingesta de datos</h2>
        <span className="note">Excel o CSV + mapeo de columnas</span>
      </header>
      <div className="panel-body">
        {error && <p className="estado-error" style={{ marginBottom: 10 }}>{error}</p>}

        <div className="ingesta-subida">
          <div
            className={`ingesta-dropzone${arrastrando ? ' arrastrando' : ''}${archivos.length ? ' con-archivo' : ''}`}
            role="button"
            tabIndex={0}
            onClick={() => inputRef.current?.click()}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click();
            }}
            onDragOver={(e) => {
              e.preventDefault();
              setArrastrando(true);
            }}
            onDragLeave={() => setArrastrando(false)}
            onDrop={onDrop}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".xlsx,.xls,.csv"
              multiple
              className="ingesta-dropzone-input"
              onChange={(e) => elegirArchivos(e.target.files)}
            />
            {archivos.length > 0 ? (
              <div className="ingesta-dropzone-lista">
                {archivos.map((archivo, i) => (
                  <div key={`${archivo.name}-${i}`} className="ingesta-dropzone-archivo">
                    <span className="ingesta-dropzone-check">✓</span>
                    <div className="ingesta-dropzone-info">
                      <p className="ingesta-dropzone-nombre mono">{archivo.name}</p>
                      <p className="ingesta-dropzone-detalle">{formatearTamano(archivo.size)}</p>
                    </div>
                    <button
                      className="boton boton-secundario"
                      onClick={(e) => {
                        e.stopPropagation();
                        quitarArchivo(i);
                      }}
                    >
                      Quitar
                    </button>
                  </div>
                ))}
                <p className="ingesta-dropzone-detalle" style={{ marginTop: 6 }}>
                  {modo === 'excel' ? 'Modo Excel' : 'Modo CSV'} · click para agregar o reemplazar
                </p>
              </div>
            ) : (
              <>
                <span className="ingesta-dropzone-flecha" aria-hidden="true">↑</span>
                <p className="ingesta-dropzone-texto">
                  <b>Arrastra tus archivos aquí</b> o haz click para buscarlos
                </p>
                <p className="ingesta-dropzone-detalle">
                  Un Excel (.xlsx/.xls) con las 6 hojas, o varios .csv sueltos (uno por tabla)
                </p>
              </>
            )}
          </div>
          <button className="boton" disabled={archivos.length === 0 || !mapeo || enviando} onClick={enviar}>
            {enviando ? 'Ingiriendo…' : 'Subir e ingerir'}
          </button>
        </div>

        {enviando && <PipelineChecklist etapaExtra="Subiendo y validando el archivo" />}

        <p style={{ fontSize: 12.5, color: 'var(--grafito2)', margin: '18px 0 12px' }}>
          Si el archivo real trae otros nombres de columna (ej. de un export de SAP MM), edítalos aquí antes de
          subir — nunca hay que tocar código para eso. En modo CSV, cada archivo se empareja por nombre contra la
          columna <span className="mono">hoja</span> de abajo (sin distinguir mayúsculas, tildes ni guiones).
        </p>

        {!mapeo ? (
          <p>Cargando mapeo…</p>
        ) : (
          <div className="ingesta-mapeo scroll">
            {Object.entries(mapeo).map(([tabla, def]) => (
              <div key={tabla} className="ingesta-tabla-mapeo">
                <h3>
                  {tabla} <span className="mono">· hoja: {def.hoja}</span>
                </h3>
                <table>
                  <thead>
                    <tr>
                      <th>Campo canónico</th>
                      <th>Columna de origen</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(def.columnas).map(([canonico, origen]) => (
                      <tr key={canonico}>
                        <td className="mono">{canonico}</td>
                        <td>
                          <input
                            className="mono"
                            value={origen}
                            onChange={(e) => editarColumna(tabla, canonico, e.target.value)}
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        )}

        {errorPrevia && <p className="estado-error" style={{ marginTop: 10 }}>{errorPrevia}</p>}

        {previa && mapeo && (
          <div className="ingesta-previa">
            {previa.map((p) => (
              <PreviaHojaVista key={p.hoja} previa={p} mapeo={mapeo} modo={modo ?? 'excel'} />
            ))}
          </div>
        )}

        {resultado && (
          <div className="ingesta-resultado">
            <p>
              <b className="mono">{resultado.filas_aceptadas}</b> filas aceptadas ·{' '}
              <b className="mono">{resultado.filas_rechazadas.length}</b> rechazadas
            </p>
            {resultado.filas_rechazadas.length > 0 && (
              <ul className="peso-lista-cambios">
                {resultado.filas_rechazadas.slice(0, 10).map((f, i) => (
                  <li key={i}>
                    <span className="mono">{f.tabla}</span> fila {f.fila}: {f.motivo}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

function PreviaHojaVista({ previa, mapeo, modo }: { previa: PreviaHoja; mapeo: Mapeo; modo: ModoArchivo }) {
  const columnasMapeadas = useMemo(() => {
    const tabla = Object.entries(mapeo).find(([, def]) => def.hoja === previa.hoja);
    if (!tabla) return [];
    const [, def] = tabla;
    return Object.entries(def.columnas).map(([canonico, origen]) => ({
      canonico,
      origen,
      encontrada: previa.encabezados.some((h) => h.trim().toLowerCase() === origen.trim().toLowerCase()),
    }));
  }, [previa, mapeo]);

  if (!previa.encontrada) {
    return (
      <div className="ingesta-previa-hoja ingesta-previa-faltante">
        {modo === 'excel' ? (
          <>
            La hoja <span className="mono">{previa.hoja}</span> no aparece en este archivo.
          </>
        ) : (
          <>
            No se subió ningún .csv que empareje con <span className="mono">{previa.hoja}</span>.
          </>
        )}
      </div>
    );
  }

  return (
    <div className="ingesta-previa-hoja">
      <h3>
        {modo === 'excel' ? 'Hoja' : 'Archivo'} <span className="mono">{previa.hoja}</span> — primeras{' '}
        {previa.filas.length} filas de datos
      </h3>
      <div className="scroll">
        <table>
          <thead>
            <tr>
              {previa.encabezados.map((h, i) => (
                <th key={i} className="mono">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {previa.filas.map((fila, i) => (
              <tr key={i}>
                {previa.encabezados.map((_, j) => (
                  <td key={j} className="mono">{String(fila[j] ?? '')}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="ingesta-previa-subtitulo">Coincidencia con el mapeo configurado</p>
      <ul className="ingesta-previa-checklist">
        {columnasMapeadas.map((c) => (
          <li key={c.canonico} className={c.encontrada ? 'ok' : 'falta'}>
            {c.encontrada ? '✓' : '✗'} <span className="mono">{c.canonico}</span> ← <span className="mono">{c.origen}</span>
            {!c.encontrada && ' (no está en el archivo)'}
          </li>
        ))}
      </ul>
    </div>
  );
}
