import { useState, useEffect, useMemo, useCallback } from "react";
import { select, update } from "../lib/insforge";

const euro = (n) =>
  Number(n).toLocaleString("es-ES", { minimumFractionDigits: 2 });

const fmtFecha = (d) => {
  if (!d) return "—";
  const [a, m, dia] = d.slice(0, 10).split("-");
  const meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
  return `${parseInt(dia)} ${meses[parseInt(m) - 1]}`;
};

const IMPACTO_COLOR = {
  critico: "bg-error-container text-error",
  alto: "bg-warning-container text-warning",
  medio: "bg-primary-fixed-dim/30 text-on-surface",
  bajo: "bg-surface-container text-on-surface-variant",
};

// ── Componente ─────────────────────────────────────────

export default function Configuracion() {
  // ── Estados ─────────────────────────────────────────

  const [habitaciones, setHabitaciones] = useState([]);
  const [temporadas, setTemporadas] = useState([]);
  const [eventos, setEventos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const [editHabitacion, setEditHabitacion] = useState(null); // id
  const [editTemporada, setEditTemporada] = useState(null);   // id

  // ── Carga inicial ──────────────────────────────────

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      select("habitaciones", { limit: 50 }),
      select("temporadas", { limit: 50 }),
      select("eventos_locales", { limit: 50 }),
    ])
      .then(([h, t, e]) => {
        if (!cancelled) {
          setHabitaciones(h ?? []);
          setTemporadas(t ?? []);
          setEventos(e ?? []);
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

  // ── Edit handlers ──────────────────────────────────

  const handleEditHabitacion = useCallback(
    async (id, field, value) => {
      const numValue = value === "" ? null : parseFloat(value);
      setHabitaciones((prev) =>
        prev.map((h) => (h.id === id ? { ...h, [field]: numValue } : h))
      );
    },
    []
  );

  const handleEditTemporada = useCallback(
    async (id, field, value) => {
      setTemporadas((prev) =>
        prev.map((t) => (t.id === id ? { ...t, [field]: value } : t))
      );
    },
    []
  );

  // ── Save ───────────────────────────────────────────

  const handleSave = useCallback(async () => {
    setSaving(true);
    setFeedback(null);
    let successCount = 0;
    let errorCount = 0;

    try {
      // Guardar habitaciones editadas
      for (const h of habitaciones) {
        if (h._dirty) {
          await update("habitaciones", h.id, {
            num_unidades: h.num_unidades,
            capacidad: h.capacidad,
            tarifa_base: h.tarifa_base,
          });
          successCount++;
        }
      }
      // Guardar temporadas editadas
      for (const t of temporadas) {
        if (t._dirty) {
          await update("temporadas", t.id, {
            multiplicador_precio: parseFloat(t.multiplicador_precio),
          });
          successCount++;
        }
      }

      setFeedback({
        type: "success",
        msg: `Configuración guardada (${successCount} cambio${successCount !== 1 ? "s" : ""}).`,
      });

      // Recargar datos limpios
      const [h, t, e] = await Promise.all([
        select("habitaciones", { limit: 50 }),
        select("temporadas", { limit: 50 }),
        select("eventos_locales", { limit: 50 }),
      ]);
      setHabitaciones(h ?? []);
      setTemporadas(t ?? []);
      setEventos(e ?? []);
    } catch (err) {
      setFeedback({ type: "error", msg: `Error al guardar: ${err.message}` });
    } finally {
      setSaving(false);
    }
  }, [habitaciones, temporadas]);

  // ── Loading / Error ────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="font-body-lg text-on-surface-variant">Cargando configuración...</p>
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

  // ── Render ─────────────────────────────────────────

  return (
    <div>
      {/* Header */}
      <div className="mb-lg">
        <h2 className="font-headline-lg text-headline-lg text-on-surface">
          Configuración del Hotel
        </h2>
        <p className="font-body-md text-body-md text-on-surface-variant mt-2">
          Gestión del inventario, tarifas, temporadas y eventos
        </p>
      </div>

      {/* Feedback */}
      {feedback && (
        <div
          className={`mb-md px-md py-sm border ${
            feedback.type === "success"
              ? "bg-success-container border-success text-success"
              : "bg-error-container border-error text-error"
          }`}
        >
          <span className="font-body-md text-body-md">{feedback.msg}</span>
        </div>
      )}

      {/* ════════════════ HABITACIONES ════════════════ */}
      <section className="mb-xl">
        <h3 className="font-headline-md text-headline-md text-on-surface mb-md">
          Habitaciones
        </h3>
        <p className="font-body-md text-body-md text-on-surface-variant mb-md">
          Gestión del inventario y tarifas base por categoría.
        </p>

        <div className="overflow-hidden bg-surface-container-lowest border border-outline-variant">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-surface-container-high/50 border-b border-outline-variant">
                  <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Tipo de habitación</th>
                  <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider text-right">Nº unidades</th>
                  <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider text-right">Capacidad</th>
                  <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider text-right">Tarifa base (€)</th>
                  <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider text-center">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/30 font-data-tabular">
                {habitaciones.map((h) => (
                  <tr key={h.id} className="hover:bg-surface-container-low/30">
                    <td className="px-6 py-4 font-semibold text-on-surface">{h.tipo}</td>
                    <td className="px-6 py-4 text-right">
                      {editHabitacion === h.id ? (
                        <input
                          type="number"
                          min="0"
                          value={h.num_unidades}
                          onChange={(e) => {
                            handleEditHabitacion(h.id, "num_unidades", e.target.value);
                            handleEditHabitacion(h.id, "_dirty", true);
                          }}
                          className="w-16 text-right bg-surface-container border border-outline-variant px-2 py-1 font-data-tabular outline-none focus:border-primary"
                        />
                      ) : (
                        h.num_unidades
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      {editHabitacion === h.id ? (
                        <input
                          type="number"
                          min="0"
                          value={h.capacidad}
                          onChange={(e) => {
                            handleEditHabitacion(h.id, "capacidad", e.target.value);
                            handleEditHabitacion(h.id, "_dirty", true);
                          }}
                          className="w-16 text-right bg-surface-container border border-outline-variant px-2 py-1 font-data-tabular outline-none focus:border-primary"
                        />
                      ) : (
                        `${h.capacidad} Pax`
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      {editHabitacion === h.id ? (
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={h.tarifa_base}
                          onChange={(e) => {
                            handleEditHabitacion(h.id, "tarifa_base", e.target.value);
                            handleEditHabitacion(h.id, "_dirty", true);
                          }}
                          className="w-20 text-right bg-surface-container border border-outline-variant px-2 py-1 font-data-tabular outline-none focus:border-primary"
                        />
                      ) : (
                        `${euro(h.tarifa_base)} €`
                      )}
                    </td>
                    <td className="px-6 py-4 text-center">
                      <button
                        onClick={() => setEditHabitacion(editHabitacion === h.id ? null : h.id)}
                        className="p-1 text-on-surface-variant hover:text-primary transition-colors"
                        title={editHabitacion === h.id ? "Cerrar edición" : "Editar"}
                      >
                        <span className="material-symbols-outlined text-lg">
                          {editHabitacion === h.id ? "close" : "edit"}
                        </span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <button
          disabled
          className="mt-md flex items-center gap-2 border border-outline-variant text-on-surface-variant px-md py-2 font-label-md uppercase tracking-wider opacity-50 cursor-not-allowed"
          title="Próximamente"
        >
          <span className="material-symbols-outlined text-lg">add</span>
          Añadir tipo
        </button>
      </section>

      {/* ════════════════ TEMPORADAS ════════════════ */}
      <section className="mb-xl">
        <h3 className="font-headline-md text-headline-md text-on-surface mb-md">
          Temporadas
        </h3>
        <p className="font-body-md text-body-md text-on-surface-variant mb-md">
          Definición de periodos y multiplicadores dinámicos.
        </p>

        <div className="overflow-hidden bg-surface-container-lowest border border-outline-variant">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-surface-container-high/50 border-b border-outline-variant">
                  <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Nombre</th>
                  <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Fecha inicio</th>
                  <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Fecha fin</th>
                  <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider text-right">Multiplicador</th>
                  <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider text-center">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/30 font-data-tabular">
                {temporadas.map((t) => (
                  <tr key={t.id} className="hover:bg-surface-container-low/30">
                    <td className="px-6 py-4 font-semibold text-on-surface">{t.nombre}</td>
                    <td className="px-6 py-4">{fmtFecha(t.fecha_inicio)}</td>
                    <td className="px-6 py-4">{fmtFecha(t.fecha_fin)}</td>
                    <td className="px-6 py-4 text-right">
                      {editTemporada === t.id ? (
                        <input
                          type="number"
                          min="0"
                          step="0.05"
                          value={t.multiplicador_precio}
                          onChange={(e) => {
                            handleEditTemporada(t.id, "multiplicador_precio", e.target.value);
                            handleEditTemporada(t.id, "_dirty", true);
                          }}
                          className="w-20 text-right bg-surface-container border border-outline-variant px-2 py-1 font-data-tabular outline-none focus:border-primary"
                        />
                      ) : (
                        `${Number(t.multiplicador_precio).toFixed(2)}x`
                      )}
                    </td>
                    <td className="px-6 py-4 text-center">
                      <button
                        onClick={() => setEditTemporada(editTemporada === t.id ? null : t.id)}
                        className="p-1 text-on-surface-variant hover:text-primary transition-colors"
                        title={editTemporada === t.id ? "Cerrar edición" : "Ajustar"}
                      >
                        <span className="material-symbols-outlined text-lg">
                          {editTemporada === t.id ? "close" : "tune"}
                        </span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* ════════════════ EVENTOS ════════════════ */}
      <section className="mb-xl">
        <h3 className="font-headline-md text-headline-md text-on-surface mb-md">
          Eventos fijos anuales
        </h3>
        <p className="font-body-md text-body-md text-on-surface-variant mb-md">
          Eventos recurrentes de Toledo con impacto en la demanda.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-md">
          {eventos.map((ev) => (
            <div
              key={ev.id}
              className="bg-surface-container-lowest border border-outline-variant p-md flex flex-col gap-3"
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-label-md text-label-md text-on-surface font-bold">
                    {ev.nombre}
                  </p>
                  <p className="font-body-sm text-body-sm text-on-surface-variant mt-1">
                    {ev.fecha_inicio && ev.fecha_fin
                      ? `${new Date(ev.fecha_inicio + "T12:00:00").toLocaleDateString("es-ES", { day: "numeric", month: "long" })} - ${new Date(ev.fecha_fin + "T12:00:00").toLocaleDateString("es-ES", { day: "numeric", month: "long" })}`
                      : "—"}
                  </p>
                </div>
                <span className="material-symbols-outlined text-on-surface-variant/40">drag_handle</span>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-outline-variant/30">
                <span className="font-label-md text-label-md text-on-surface-variant">Impacto</span>
                <span className={`px-2 py-0.5 rounded-sm font-label-md text-label-sm font-bold uppercase ${IMPACTO_COLOR[ev.impacto_estimado] || "bg-surface-container text-on-surface-variant"}`}>
                  {ev.impacto_estimado}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="font-label-md text-label-md text-on-surface-variant">Tipo</span>
                <span className="font-body-sm text-body-sm text-on-surface capitalize">{ev.tipo}</span>
              </div>
            </div>
          ))}
        </div>

        <button
          disabled
          className="mt-md flex items-center gap-2 text-primary hover:text-primary-fixed-dim transition-colors font-label-md uppercase tracking-wider cursor-not-allowed opacity-60"
          title="Próximamente"
        >
          <span className="material-symbols-outlined text-lg">add_circle</span>
          Añadir evento fijo
        </button>
      </section>

      {/* ════════════════ GUARDAR ════════════════ */}
      <div className="border-t border-outline-variant pt-lg flex justify-end">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 bg-primary text-on-primary px-xl py-md font-label-md font-bold uppercase tracking-wider hover:bg-primary-fixed-dim transition-colors disabled:opacity-50"
        >
          <span className="material-symbols-outlined text-lg">save</span>
          {saving ? "Guardando..." : "Guardar configuración"}
        </button>
      </div>
    </div>
  );
}
