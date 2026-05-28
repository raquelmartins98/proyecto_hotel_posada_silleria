import { useState, useEffect, useMemo, useCallback } from "react";
import { select, create, update } from "../lib/insforge";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

// ── Constantes ─────────────────────────────────────────

const MESES = [
  { value: 1, label: "Enero" },
  { value: 2, label: "Febrero" },
  { value: 3, label: "Marzo" },
  { value: 4, label: "Abril" },
  { value: 5, label: "Mayo" },
  { value: 6, label: "Junio" },
  { value: 7, label: "Julio" },
  { value: 8, label: "Agosto" },
  { value: 9, label: "Septiembre" },
  { value: 10, label: "Octubre" },
  { value: 11, label: "Noviembre" },
  { value: 12, label: "Diciembre" },
];

const MES_CORTO = [
  "",
  "ENE",
  "FEB",
  "MAR",
  "ABR",
  "MAY",
  "JUN",
  "JUL",
  "AGO",
  "SEP",
  "OCT",
  "NOV",
  "DIC",
];

const CATEGORIAS = [
  { key: "costes_operativos", label: "Costes operativos", desc: "Limpieza, Amenities, Lavandería" },
  { key: "mantenimiento", label: "Mantenimiento", desc: "Reparaciones, Jardinería, Piscina" },
  { key: "personal", label: "Personal / Staff", desc: "Sueldos, Seguros, Formación" },
  { key: "suministros", label: "Suministros", desc: "Agua, Electricidad, Gas, WiFi" },
  { key: "otros", label: "Otros costes", desc: "Seguros, Tasas, Marketing" },
];

const COLORES = {
  costes_operativos: "#4A7CC7",
  mantenimiento: "#43A047",
  personal: "#EF6C00",
  suministros: "#00ACC1",
  otros: "#7B1FA2",
};

const MONTH = new Date().getMonth() + 1; // 1-12
const YEAR = new Date().getFullYear();

// ── Formateo numérico ──────────────────────────────────

const euro = (n) =>
  Number(n).toLocaleString("es-ES", { minimumFractionDigits: 2 });

/**
 * Convierte un string en formato español (coma decimal, punto miles)
 * a número. Ejemplos:
 *   "8.427,20" → 8427.20
 *   "1234,56"  → 1234.56
 *   "8.427"    → 8427
 *   ""         → 0
 */
function parseNum(str) {
  if (str == null) return 0;
  let s = String(str).trim();
  if (s === "") return 0;
  if (s.includes(",")) {
    // Formato español: punto como separador de miles, coma decimal
    s = s.replace(/\./g, "");   // quitar puntos (miles)
    s = s.replace(",", ".");     // coma → punto decimal
  } else {
    // Sin coma: quitar puntos (miles) por si acaso
    s = s.replace(/\./g, "");
  }
  return parseFloat(s) || 0;
}

// ── Componente ──────────────────────────────────────────

export default function Costes() {
  // Datos
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Formulario
  const [mes, setMes] = useState(MONTH);
  const [anio, setAnio] = useState(YEAR);
  const [campos, setCampos] = useState({
    costes_operativos: "",
    mantenimiento: "",
    personal: "",
    suministros: "",
    otros: "",
  });
  const [editingId, setEditingId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState(null); // { type, msg }

  // ── Carga inicial ──────────────────────────────────

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    select("costes_mensuales", {
      order: "anio.desc,mes.desc",
      limit: 100,
    })
      .then((data) => {
        if (!cancelled) {
          setRecords(data ?? []);
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

  // ── Pre-cargar formulario al cambiar mes/año ──────

  const existingRecord = useMemo(() => {
    return records.find((r) => r.mes === mes && r.anio === anio) ?? null;
  }, [records, mes, anio]);

  useEffect(() => {
    if (existingRecord) {
      setCampos({
        costes_operativos: String(existingRecord.costes_operativos ?? ""),
        mantenimiento: String(existingRecord.mantenimiento ?? ""),
        personal: String(existingRecord.personal ?? ""),
        suministros: String(existingRecord.suministros ?? ""),
        otros: String(existingRecord.otros ?? ""),
      });
      setEditingId(existingRecord.id);
    } else {
      setCampos({
        costes_operativos: "",
        mantenimiento: "",
        personal: "",
        suministros: "",
        otros: "",
      });
      setEditingId(null);
    }
  }, [existingRecord]);

  // ── Total calculado ────────────────────────────────

  const total = useMemo(() => {
    const vals = Object.values(campos).map((v) => parseNum(v));
    return vals.reduce((a, b) => a + b, 0);
  }, [campos]);

  // ── Handlers ───────────────────────────────────────

  const handleChange = useCallback((key, value) => {
    // Permitir solo dígitos, coma, punto y vacío
    if (value === "" || /^[\d,.]*$/.test(value)) {
      setCampos((prev) => ({ ...prev, [key]: value }));
    }
  }, []);

  const handleSave = useCallback(async () => {
    const payload = {};
    let hasValue = false;
    for (const { key } of CATEGORIAS) {
      const v = parseNum(campos[key]);
      payload[key] = v;
      if (v > 0) hasValue = true;
    }
    if (!hasValue) {
      setFeedback({ type: "warning", msg: "Introduce al menos un valor antes de guardar." });
      return;
    }
    payload.mes = mes;
    payload.anio = anio;
    payload.total = total;

    setSaving(true);
    setFeedback(null);
    try {
      if (editingId) {
        // Actualizar registro existente
        await update("costes_mensuales", editingId, payload);
        setFeedback({ type: "success", msg: "Registro actualizado correctamente." });
      } else {
        // Crear nuevo registro
        const created = await create("costes_mensuales", payload);
        if (created && created.length > 0) {
          setEditingId(created[0].id);
        }
        setFeedback({ type: "success", msg: "Registro guardado correctamente." });
      }
      // Recargar datos
      const updated = await select("costes_mensuales", {
        order: "anio.desc,mes.desc",
        limit: 100,
      });
      setRecords(updated ?? []);
    } catch (err) {
      setFeedback({ type: "error", msg: `Error al guardar: ${err.message}` });
    } finally {
      setSaving(false);
    }
  }, [campos, mes, anio, total, editingId]);

  // ── Datos para el gráfico ─────────────────────────

  const chartData = useMemo(() => {
    const sorted = [...records].sort((a, b) =>
      a.anio !== b.anio ? a.anio - b.anio : a.mes - b.mes
    );
    return sorted.map((r) => ({
      mes: MES_CORTO[r.mes] ?? r.mes,
      costes_operativos: r.costes_operativos ?? 0,
      mantenimiento: r.mantenimiento ?? 0,
      personal: r.personal ?? 0,
      suministros: r.suministros ?? 0,
      otros: r.otros ?? 0,
    }));
  }, [records]);

  // ── Años disponibles ──────────────────────────────

  const añosDisponibles = useMemo(() => {
    const años = new Set(records.map((r) => r.anio));
    años.add(YEAR);
    return [...años].sort((a, b) => b - a);
  }, [records]);

  // ── Render ─────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="font-body-lg text-on-surface-variant">Cargando costes...</p>
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

  return (
    <div>
      {/* ── Header ─────────────────────────────────── */}
      <div className="mb-lg">
        <h2 className="font-headline-lg text-headline-lg text-on-surface">
          Costes reales
        </h2>
        <p className="font-body-md text-body-md text-on-surface-variant mt-2">
          Registro mensual de costes operativos del hotel
        </p>
      </div>

      {/* ── Feedback ───────────────────────────────── */}
      {feedback && (
        <div
          className={`mb-md px-md py-sm border ${
            feedback.type === "success"
              ? "bg-success-container border-success text-success"
              : feedback.type === "warning"
                ? "bg-warning-container border-warning text-warning"
                : "bg-error-container border-error text-error"
          }`}
        >
          <span className="font-body-md text-body-md">{feedback.msg}</span>
        </div>
      )}

      {/* ── Grid principal: Formulario + Gráfico ──── */}
      <div className="bento-grid mb-lg">
        {/* Columna izquierda — Formulario */}
        <div className="col-span-12 lg:col-span-5 bg-surface-container-lowest border border-outline-variant p-lg">
          <h3 className="font-headline-sm text-headline-sm text-on-surface mb-md">
            Registro mensual
          </h3>

          {/* Selector mes/año */}
          <div className="flex gap-sm mb-lg">
            <div className="flex-1">
              <label className="block font-label-md text-label-md text-on-surface-variant mb-1">
                Mes
              </label>
              <select
                value={mes}
                onChange={(e) => setMes(Number(e.target.value))}
                className="w-full bg-surface-container border border-outline-variant px-sm py-sm font-body-md text-on-surface outline-none focus:border-primary"
              >
                {MESES.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex-1">
              <label className="block font-label-md text-label-md text-on-surface-variant mb-1">
                Año
              </label>
              <select
                value={anio}
                onChange={(e) => setAnio(Number(e.target.value))}
                className="w-full bg-surface-container border border-outline-variant px-sm py-sm font-body-md text-on-surface outline-none focus:border-primary"
              >
                {añosDisponibles.map((a) => (
                  <option key={a} value={a}>
                    {a}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Campos de costes */}
          <div className="space-y-md">
            {CATEGORIAS.map(({ key, label, desc }) => (
              <div key={key}>
                <label className="block font-label-md text-label-md text-on-surface mb-1">
                  {label}
                </label>
                <input
                  type="text"
                  inputMode="decimal"
                  value={campos[key]}
                  onChange={(e) => handleChange(key, e.target.value)}
                  placeholder="0,00"
                  className="w-full bg-surface-container border border-outline-variant px-sm py-sm font-body-md text-on-surface outline-none focus:border-primary text-right font-data-tabular"
                />
                <p className="font-body-sm text-body-sm text-on-surface-variant mt-1">
                  {desc}
                </p>
              </div>
            ))}
          </div>

          {/* Total */}
          <div className="mt-lg pt-md border-t border-outline-variant">
            <div className="flex items-center justify-between">
              <span className="font-label-lg text-label-lg text-on-surface">
                Total mensual acumulado
              </span>
              <span className="font-headline-md text-headline-md text-primary font-bold font-data-tabular">
                {euro(total)} €
              </span>
            </div>
          </div>

          {/* Botones */}
          <div className="mt-lg flex flex-wrap gap-sm">
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-2 bg-primary text-on-primary px-md py-sm font-label-md font-bold uppercase tracking-wider hover:bg-primary-fixed-dim transition-colors disabled:opacity-50"
            >
              <span className="material-symbols-outlined text-lg">save</span>
              {saving ? "Guardando..." : "Guardar registro"}
            </button>
            <button
              type="button"
              disabled
              className="flex items-center gap-2 border border-outline-variant text-on-surface-variant px-md py-sm font-label-md uppercase tracking-wider opacity-50 cursor-not-allowed"
              title="Próximamente"
            >
              <span className="material-symbols-outlined text-lg">upload_file</span>
              Importar Excel/CSV
            </button>
          </div>
        </div>

        {/* Columna derecha — Gráfico */}
        <div className="col-span-12 lg:col-span-7 bg-surface-container-lowest border border-outline-variant p-lg">
          <h3 className="font-headline-sm text-headline-sm text-on-surface mb-1">
            Evolución mensual
          </h3>
          <p className="font-body-md text-body-md text-on-surface-variant mb-md">
            Comparativa de costes de los últimos 12 meses
          </p>
          <p className="font-body-sm text-body-sm text-on-surface-variant mb-lg">
            Datos expresados en euros
          </p>

          {chartData.length === 0 ? (
            <div className="flex items-center justify-center h-80 bg-surface-container/30 border border-dashed border-outline-variant">
              <p className="font-body-md text-on-surface-variant">
                No hay datos para mostrar el gráfico
              </p>
            </div>
          ) : (
            <div className="h-80 sm:h-96">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={chartData}
                  margin={{ top: 8, right: 8, left: -8, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                  <XAxis
                    dataKey="mes"
                    tick={{ fontSize: 11, fontWeight: 600 }}
                    stroke="#9e9e9e"
                  />
                  <YAxis tick={{ fontSize: 11 }} stroke="#9e9e9e" />
                  <Tooltip
                    contentStyle={{
                      background: "#fff",
                      border: "1px solid #e0e0e0",
                      borderRadius: 4,
                      fontSize: 13,
                    }}
                    formatter={(value) => `${euro(value)} €`}
                  />
                  <Legend
                    wrapperStyle={{ fontSize: 11 }}
                    iconType="square"
                    iconSize={10}
                  />
                  {CATEGORIAS.map(({ key, label }) => (
                    <Bar
                      key={key}
                      dataKey={key}
                      name={label}
                      stackId="costes"
                      fill={COLORES[key]}
                      radius={[2, 2, 0, 0]}
                    />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>

      {/* ── Tarjetas de información ────────────────── */}
      <div className="bento-grid">
        {/* Optimización */}
        <div className="col-span-12 sm:col-span-6 lg:col-span-4 bg-surface-container-lowest border border-outline-variant p-md flex gap-md">
          <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center bg-success-container text-success">
            <span className="material-symbols-outlined text-xl">lightbulb</span>
          </div>
          <div>
            <h4 className="font-label-md text-label-md text-on-surface font-bold uppercase tracking-wider mb-1">
              Optimización
            </h4>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              El coste de suministros ha bajado un{" "}
              <strong className="text-success">
                {(() => {
                  if (chartData.length < 2) return "4%";
                  const ultimo = chartData[chartData.length - 1];
                  const anterior = chartData[chartData.length - 2];
                  if (!anterior || !ultimo) return "4%";
                  const diff =
                    ((anterior.suministros - ultimo.suministros) /
                      anterior.suministros) *
                    100;
                  if (diff <= 0) return "—";
                  return `${Math.round(diff)}%`;
                })()}
              </strong>{" "}
              respecto al mes anterior tras el ajuste de climatización.
            </p>
          </div>
        </div>

        {/* Alertas de Personal */}
        <div className="col-span-12 sm:col-span-6 lg:col-span-4 bg-surface-container-lowest border border-outline-variant p-md flex gap-md">
          <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center bg-warning-container text-warning">
            <span className="material-symbols-outlined text-xl">assignment_late</span>
          </div>
          <div>
            <h4 className="font-label-md text-label-md text-on-surface font-bold uppercase tracking-wider mb-1">
              Alertas de Personal
            </h4>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Se prevé un incremento del{" "}
              <strong className="text-warning">15%</strong> en gastos de
              personal para los próximos meses por festividades.
            </p>
          </div>
        </div>

        {/* Histórico */}
        <div className="col-span-12 sm:col-span-6 lg:col-span-4 bg-surface-container-lowest border border-outline-variant p-md flex gap-md">
          <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center bg-primary-fixed-dim text-primary">
            <span className="material-symbols-outlined text-xl">history_edu</span>
          </div>
          <div>
            <h4 className="font-label-md text-label-md text-on-surface font-bold uppercase tracking-wider mb-1">
              Histórico
            </h4>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Puedes consultar los informes auditados de años anteriores en la
              sección de Configuración.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
