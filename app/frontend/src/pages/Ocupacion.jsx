import { useState, useEffect, useMemo, useCallback } from "react";
import { select } from "../lib/insforge";

// ── Constantes ─────────────────────────────────────────

const MESES = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];

const DIAS_SEMANA = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];

// Mapeo día-semana JS (0=Dom) → Lun=0
const DIA_OFFSET = { 0: 6, 1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5 };

const HOY = new Date();

// ── Utilidades ──────────────────────────────────────────

const fmtFecha = (d) => d.toISOString().slice(0, 10);

function diasEnMes(anio, mes) {
  return new Date(anio, mes + 1, 0).getDate();
}

function primerDiaSem(anio, mes) {
  // Devuelve 0=Lun ... 6=Dom
  const d = new Date(anio, mes, 1).getDay();
  return DIA_OFFSET[d];
}

const euro = (n) =>
  Number(n).toLocaleString("es-ES", { minimumFractionDigits: 0 });

// ── Color de ocupación (gradiente 0% → 100%) ──────────
function colorOcupacion(pct) {
  if (pct == null) return "bg-surface-container";
  const v = Math.min(Math.max(pct, 0), 100);
  if (v < 20) return "bg-primary-fixed-dim/20";
  if (v < 40) return "bg-primary-fixed-dim/40";
  if (v < 60) return "bg-primary-fixed-dim/60";
  if (v < 80) return "bg-primary/70";
  return "bg-primary";
}

function textColorOcupacion(pct) {
  if (pct == null) return "";
  return pct >= 60 ? "text-white" : "text-on-surface";
}

// ── Componente ─────────────────────────────────────────

export default function Ocupacion() {
  // Tabs
  const [tab, setTab] = useState("ocupacion");

  // Datos
  const [ocupacion, setOcupacion] = useState([]);
  const [incidencias, setIncidencias] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Calendario
  const [calMes, setCalMes] = useState(HOY.getMonth());
  const [calAnio, setCalAnio] = useState(HOY.getFullYear());
  const [diaSeleccionado, setDiaSeleccionado] = useState(null);

  // ── Carga inicial ──────────────────────────────────

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      select("ocupacion_real", {
        select: "fecha,porcentaje_ocupacion,habitaciones_ocupadas,habitaciones_totales",
        order: "fecha.asc",
        limit: 500,
      }),
      select("incidencias", { limit: 50 }).catch(() => []),
    ])
      .then(([ocu, inc]) => {
        if (!cancelled) {
          setOcupacion(ocu ?? []);
          setIncidencias(inc ?? []);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // ── Mapa días → datos ─────────────────────────────

  const diaMap = useMemo(() => {
    const map = {};
    for (const r of ocupacion) {
      if (r.fecha) map[r.fecha.slice(0, 10)] = r;
    }
    return map;
  }, [ocupacion]);

  // ── Datos del mes actual ──────────────────────────

  const mesData = useMemo(() => {
    const totalDias = diasEnMes(calAnio, calMes);
    const offset = primerDiaSem(calAnio, calMes);
    const days = [];

    for (let i = 0; i < offset; i++) {
      days.push({ empty: true });
    }

    let sumaPct = 0;
    let countPct = 0;
    let maxPct = 0;
    let maxFecha = null;

    for (let d = 1; d <= totalDias; d++) {
      const fecha = `${calAnio}-${String(calMes + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      const record = diaMap[fecha] ?? null;
      const pct = record ? Number(record.porcentaje_ocupacion) : null;

      if (pct != null) {
        sumaPct += pct;
        countPct++;
        if (pct > maxPct) {
          maxPct = pct;
          maxFecha = fecha;
        }
      }

      days.push({ day: d, fecha, record, pct, hoy: fecha === fmtFecha(HOY) });
    }

    const media = countPct > 0 ? Math.round(sumaPct / countPct) : 0;

    return { days, media, maxPct, maxFecha, totalDias, countPct };
  }, [calAnio, calMes, diaMap]);

  // ── Navegación calendario ─────────────────────────

  const mesAnterior = useCallback(() => {
    setCalMes((m) => {
      if (m === 0) {
        setCalAnio((a) => a - 1);
        return 11;
      }
      return m - 1;
    });
    setDiaSeleccionado(null);
  }, []);

  const mesSiguiente = useCallback(() => {
    setCalMes((m) => {
      if (m === 11) {
        setCalAnio((a) => a + 1);
        return 0;
      }
      return m + 1;
    });
    setDiaSeleccionado(null);
  }, []);

  const diaClick = useCallback((fecha) => {
    setDiaSeleccionado((prev) => (prev === fecha ? null : fecha));
  }, []);

  // ── Calcular "mes anterior" para comparativa ──────

  const comparativa = useMemo(() => {
    if (ocupacion.length < 60) return null;
    // Promedio del mes actual vs mismo mes año anterior
    const actual = mesData.media;
    const anioAnt = calAnio - 1;
    let suma = 0;
    let cont = 0;
    const totalDiasAnt = diasEnMes(anioAnt, calMes);
    for (let d = 1; d <= totalDiasAnt; d++) {
      const f = `${anioAnt}-${String(calMes + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      const r = diaMap[f];
      if (r?.porcentaje_ocupacion != null) {
        suma += Number(r.porcentaje_ocupacion);
        cont++;
      }
    }
    const antMedia = cont > 0 ? Math.round(suma / cont) : 0;
    if (antMedia === 0) return null;
    return { actual, anterior: antMedia, diff: actual - antMedia };
  }, [calAnio, calMes, mesData.media, diaMap, ocupacion.length]);

  // ── Previsión mes siguiente ───────────────────────

  const prevision = useMemo(() => {
    const mesSig = calMes === 11 ? 0 : calMes + 1;
    const anioSig = calMes === 11 ? calAnio + 1 : calAnio;
    let suma = 0;
    let cont = 0;
    const total = diasEnMes(anioSig, mesSig);
    for (let d = 1; d <= total; d++) {
      const f = `${anioSig}-${String(mesSig + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      const r = diaMap[f];
      if (r?.porcentaje_ocupacion != null) {
        suma += Number(r.porcentaje_ocupacion);
        cont++;
      }
    }
    if (cont === 0) return null;
    return Math.round(suma / cont);
  }, [calMes, calAnio, diaMap]);

  // ── Dia seleccionado en detalle ───────────────────

  const detalleDia = useMemo(() => {
    if (!diaSeleccionado) return null;
    const r = diaMap[diaSeleccionado];
    if (!r) return { fecha: diaSeleccionado, pct: null };
    return {
      fecha: diaSeleccionado,
      pct: Number(r.porcentaje_ocupacion),
      ocupadas: Number(r.habitaciones_ocupadas),
      totales: Number(r.habitaciones_totales),
    };
  }, [diaSeleccionado, diaMap]);

  // ── Render: loading / error ───────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="font-body-lg text-on-surface-variant">Cargando ocupación...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-error-container border border-error p-md">
        <p className="font-body-md text-error">Error al cargar: {error}</p>
      </div>
    );
  }

  // ── Render principal ──────────────────────────────

  return (
    <div>
      {/* Header */}
      <div className="mb-lg">
        <h2 className="font-headline-lg text-headline-lg text-on-surface">
          Ocupación e incidencias
        </h2>
        <p className="font-body-md text-body-md text-on-surface-variant mt-2">
          Ocupación histórica y gestión de bloqueos del hotel
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-outline-variant mb-lg">
        <button
          onClick={() => setTab("ocupacion")}
          className={`px-md py-sm font-label-md uppercase tracking-wider transition-colors ${
            tab === "ocupacion"
              ? "text-primary border-b-2 border-primary font-bold"
              : "text-on-surface-variant hover:text-on-surface"
          }`}
        >
          Ocupación real
        </button>
        <button
          onClick={() => setTab("incidencias")}
          className={`px-md py-sm font-label-md uppercase tracking-wider transition-colors ${
            tab === "incidencias"
              ? "text-primary border-b-2 border-primary font-bold"
              : "text-on-surface-variant hover:text-on-surface"
          }`}
        >
          Incidencias
        </button>
      </div>

      {/* ═══════════════ TAB: OCUPACIÓN ═══════════════ */}
      {tab === "ocupacion" && (
        <div className="bento-grid">
          {/* ── Calendario ─────────────────────────── */}
          <div className="col-span-12 lg:col-span-8 bg-surface-container-lowest border border-outline-variant p-lg">
            {/* Cabecera calendario */}
            <div className="flex items-center justify-between mb-md">
              <h3 className="font-headline-sm text-headline-sm text-on-surface">
                Calendario de Ocupación
              </h3>
              <button
                type="button"
                disabled
                className="flex items-center gap-2 border border-outline-variant text-on-surface-variant px-sm py-1 font-label-md text-label-sm uppercase tracking-wider opacity-50 cursor-not-allowed"
                title="Próximamente"
              >
                <span className="material-symbols-outlined text-base">upload_file</span>
                Importar Excel/CSV
              </button>
            </div>

            {/* Navegación mes */}
            <div className="flex items-center justify-between mb-md">
              <button
                onClick={mesAnterior}
                className="flex items-center gap-1 text-on-surface-variant hover:text-on-surface transition-colors font-label-md"
              >
                <span className="material-symbols-outlined">chevron_left</span>
                {MESES[calMes === 0 ? 11 : calMes - 1]}
              </button>
              <span className="font-headline-md text-headline-md text-on-surface">
                {MESES[calMes]} {calAnio}
              </span>
              <button
                onClick={mesSiguiente}
                className="flex items-center gap-1 text-on-surface-variant hover:text-on-surface transition-colors font-label-md"
              >
                {MESES[calMes === 11 ? 0 : calMes + 1]}
                <span className="material-symbols-outlined">chevron_right</span>
              </button>
            </div>

            {/* Grid calendario */}
            <div className="grid grid-cols-7 gap-[2px]">
              {/* Días de la semana */}
              {DIAS_SEMANA.map((d) => (
                <div
                  key={d}
                  className="text-center py-2 font-label-md text-label-sm text-on-surface-variant uppercase tracking-wider"
                >
                  {d}
                </div>
              ))}

              {/* Días del mes */}
              {mesData.days.map((d, i) =>
                d.empty ? (
                  <div key={`e-${i}`} className="aspect-square" />
                ) : (
                  <button
                    key={d.fecha}
                    onClick={() => diaClick(d.fecha)}
                    className={`relative aspect-square flex flex-col items-center justify-center rounded-sm text-sm transition-all ${
                      colorOcupacion(d.pct)
                    } ${textColorOcupacion(d.pct)} ${
                      d.hoy ? "ring-2 ring-primary ring-offset-1" : ""
                    } ${
                      diaSeleccionado === d.fecha
                        ? "ring-2 ring-on-surface ring-offset-1"
                        : ""
                    } cursor-pointer hover:scale-105`}
                    title={`${d.day} — ${d.pct != null ? d.pct + "%" : "sin datos"}`}
                  >
                    <span className="font-label-md text-label-sm leading-none">
                      {d.day}
                    </span>
                    {d.pct != null && (
                      <span className="text-[9px] leading-none mt-[2px] opacity-80">
                        {Math.round(d.pct)}%
                      </span>
                    )}
                  </button>
                )
              )}
            </div>

            {/* Leyenda */}
            <div className="flex items-center gap-2 mt-md pt-sm border-t border-outline-variant">
              <span className="font-label-md text-label-sm text-on-surface-variant">
                Leyenda de ocupación:
              </span>
              <div className="flex items-center gap-1">
                <span className="text-label-sm text-on-surface-variant">0%</span>
                <div className="flex h-3 w-32 rounded-sm overflow-hidden">
                  <div className="w-1/5 bg-primary-fixed-dim/20" />
                  <div className="w-1/5 bg-primary-fixed-dim/40" />
                  <div className="w-1/5 bg-primary-fixed-dim/60" />
                  <div className="w-1/5 bg-primary/70" />
                  <div className="w-1/5 bg-primary" />
                </div>
                <span className="text-label-sm text-on-surface-variant">100%</span>
              </div>
            </div>
          </div>

          {/* ── Sidebar stats ──────────────────────── */}
          <div className="col-span-12 lg:col-span-4 flex flex-col gap-md">
            {/* Media del mes */}
            <div className="bg-surface-container-lowest border border-outline-variant p-md">
              <p className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider mb-1">
                Media del mes
              </p>
              <p className="font-headline-lg text-headline-lg text-on-surface font-bold">
                {mesData.media}%
              </p>
              {comparativa && (
                <div className="flex items-center gap-1 mt-1">
                  <span className={`material-symbols-outlined text-sm ${comparativa.diff >= 0 ? "text-success" : "text-error"}`}>
                    {comparativa.diff >= 0 ? "trending_up" : "trending_down"}
                  </span>
                  <span className={`font-label-md text-label-sm ${comparativa.diff >= 0 ? "text-success" : "text-error"}`}>
                    {comparativa.diff >= 0 ? "+" : ""}{comparativa.diff}% respecto a {MESES[calMes]} {calAnio - 1}
                  </span>
                </div>
              )}
            </div>

            {/* Pico de Ocupación */}
            <div className="bg-surface-container-lowest border border-outline-variant p-md">
              <p className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider mb-1">
                Pico de Ocupación
              </p>
              <p className="font-headline-lg text-headline-lg text-primary font-bold">
                {mesData.maxPct > 0 ? Math.round(mesData.maxPct) : "—"}%
              </p>
              {mesData.maxFecha && (
                <p className="font-body-sm text-body-sm text-on-surface-variant mt-1">
                  {new Date(mesData.maxFecha + "T12:00:00").toLocaleDateString("es-ES", {
                    weekday: "long",
                    day: "numeric",
                    month: "long",
                  })}
                </p>
              )}
            </div>

            {/* Previsión mes siguiente */}
            <div className="bg-surface-container-lowest border border-outline-variant p-md">
              <p className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider mb-1">
                Previsión {MESES[calMes === 11 ? 0 : calMes + 1]}
              </p>
              <p className="font-headline-lg text-headline-lg text-on-surface font-bold">
                {prevision != null ? prevision + "%" : "—"}
              </p>
              <p className="font-body-sm text-body-sm text-on-surface-variant mt-1">
                {prevision != null
                  ? `Basado en ${mesData.countPct} días registrados`
                  : "Sin datos disponibles"}
              </p>
            </div>

            {/* Detalle del día seleccionado */}
            {detalleDia && (
              <div className="bg-primary-fixed-dim/10 border border-primary/30 p-md">
                <p className="font-label-md text-label-md text-primary uppercase tracking-wider mb-1">
                  {new Date(detalleDia.fecha + "T12:00:00").toLocaleDateString("es-ES", {
                    weekday: "long",
                    day: "numeric",
                    month: "long",
                    year: "numeric",
                  })}
                </p>
                <div className="flex justify-between items-baseline mt-2">
                  <span className="font-body-md text-body-md text-on-surface">Ocupación</span>
                  <span className="font-headline-md text-headline-md text-primary font-bold">
                    {detalleDia.pct != null ? Math.round(detalleDia.pct) + "%" : "—"}
                  </span>
                </div>
                {detalleDia.ocupadas != null && (
                  <div className="flex justify-between items-baseline mt-1">
                    <span className="font-body-sm text-body-sm text-on-surface-variant">Habitaciones</span>
                    <span className="font-label-md text-label-md text-on-surface">
                      {detalleDia.ocupadas} de {detalleDia.totales}
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ═══════════════ TAB: INCIDENCIAS ═══════════════ */}
      {tab === "incidencias" && (
        <div className="bg-surface-container-lowest border border-outline-variant">
          {/* Cabecera */}
          <div className="flex items-center justify-between p-lg border-b border-outline-variant">
            <div>
              <h3 className="font-headline-sm text-headline-sm text-on-surface">
                Registro de Incidencias
              </h3>
              <p className="font-body-md text-body-md text-on-surface-variant mt-1">
                Gestión de bloqueos, reparaciones y mantenimiento de habitaciones.
              </p>
            </div>
            <button
              type="button"
              disabled
              className="flex items-center gap-2 bg-primary text-on-primary px-md py-sm font-label-md font-bold uppercase tracking-wider opacity-50 cursor-not-allowed"
              title="Requiere inicio de sesión"
            >
              <span className="material-symbols-outlined text-lg">add</span>
              Nueva incidencia
            </button>
          </div>

          {/* Tabla */}
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-surface-container-high/50 border-b border-outline-variant">
                  <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Habitación</th>
                  <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Fecha desde</th>
                  <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Fecha hasta</th>
                  <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Motivo</th>
                  <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Notas</th>
                  <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/30 font-data-tabular">
                {incidencias.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center">
                      <div className="flex flex-col items-center gap-2">
                        <span className="material-symbols-outlined text-3xl text-on-surface-variant/50">lock</span>
                        <p className="font-body-md text-body-md text-on-surface-variant">
                          Las incidencias requieren inicio de sesión
                        </p>
                        <p className="font-body-sm text-body-sm text-on-surface-variant/70">
                          Próximamente: autenticación de usuarios
                        </p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  incidencias.map((inc) => (
                    <tr key={inc.id} className="hover:bg-surface-container-low/30">
                      <td className="px-6 py-4 font-semibold text-on-surface">{inc.habitacion}</td>
                      <td className="px-6 py-4">{inc.fecha_desde?.slice(0, 10)}</td>
                      <td className="px-6 py-4">{inc.fecha_hasta?.slice(0, 10) ?? "—"}</td>
                      <td className="px-6 py-4">
                        <span className={`inline-block px-2 py-0.5 rounded-sm font-label-md text-label-sm ${
                          inc.motivo === "fuera de servicio" ? "bg-error-container text-error" :
                          inc.motivo === "obras" ? "bg-warning-container text-warning" :
                          inc.motivo === "cierre" ? "bg-primary-fixed-dim/30 text-on-surface" :
                          "bg-surface-container text-on-surface-variant"
                        }`}>
                          {inc.motivo}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-on-surface-variant max-w-xs truncate">{inc.notas}</td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-1">
                          <button disabled className="p-1 text-on-surface-variant/40 cursor-not-allowed" title="Editar">
                            <span className="material-symbols-outlined text-lg">edit</span>
                          </button>
                          <button disabled className="p-1 text-on-surface-variant/40 cursor-not-allowed" title="Eliminar">
                            <span className="material-symbols-outlined text-lg">delete</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
