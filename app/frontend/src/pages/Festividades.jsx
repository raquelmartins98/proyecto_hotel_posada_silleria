import { useInsforgeQuery, useInsforgeMutate } from "../hooks/useInsforge";
import { useState } from "react";

export default function Festividades() {
  const { data: eventos, loading, error, refetch } = useInsforgeQuery(
    "SELECT nombre, tipo, impacto_estimado, fecha_inicio, fecha_fin FROM public.eventos_locales ORDER BY fecha_inicio"
  );
  const { run: crearEvento, loading: saving, error: saveError, success } = useInsforgeMutate();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ nombre: "", tipo: "", impacto: "medio", inicio: "", fin: "" });

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await crearEvento(
        `INSERT INTO public.eventos_locales (nombre, tipo, impacto_estimado, fecha_inicio, fecha_fin)
         VALUES ($1, $2, $3, $4::date, $5::date)`,
        [form.nombre, form.tipo, form.impacto, form.inicio, form.fin]
      );
      setShowForm(false);
      setForm({ nombre: "", tipo: "", impacto: "medio", inicio: "", fin: "" });
      refetch();
    } catch {}
  };

  return (
    <div>
      <div className="flex justify-between items-start mb-lg">
        <div>
          <h2 className="font-headline-lg text-headline-lg text-on-surface">
            Festividades y eventos
          </h2>
          <p className="font-body-md text-body-md text-on-surface-variant mt-2">
            Eventos locales que afectan a la demanda y los precios
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-primary text-on-primary px-6 py-3 font-label-md uppercase tracking-widest flex items-center gap-2 rounded-sm"
        >
          <span className="material-symbols-outlined">add</span>
          Nuevo evento
        </button>
      </div>

      {/* Create Form */}
      {showForm && (
        <div className="bg-surface-container-lowest border border-outline-variant p-md mb-6">
          <h3 className="font-headline-md text-headline-md text-on-surface mb-4">Nuevo evento local</h3>
          {saveError && (
            <div className="bg-error-container border border-error text-on-error-container px-4 py-3 mb-4 font-body-md rounded-sm">
              {saveError}
            </div>
          )}
          {success && (
            <div className="bg-success-container border border-success text-success px-4 py-3 mb-4 font-body-md rounded-sm">
              Evento creado correctamente
            </div>
          )}
          <form onSubmit={handleSubmit} className="bento-grid">
            <div className="col-span-12 sm:col-span-6 flex flex-col gap-1">
              <label className="text-[10px] text-on-surface-variant uppercase font-bold">Nombre del evento</label>
              <input
                className="w-full px-4 py-2 bg-surface-container border border-outline-variant focus:outline-none focus:border-primary transition-colors font-body-md"
                value={form.nombre}
                onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                required
              />
            </div>
            <div className="col-span-12 sm:col-span-3 flex flex-col gap-1">
              <label className="text-[10px] text-on-surface-variant uppercase font-bold">Tipo</label>
              <select
                className="w-full px-4 py-2 bg-surface-container border border-outline-variant focus:outline-none focus:border-primary transition-colors font-body-md"
                value={form.tipo}
                onChange={(e) => setForm({ ...form, tipo: e.target.value })}
                required
              >
                <option value="">Seleccionar...</option>
                <option value="religioso">Religioso</option>
                <option value="cultural">Cultural</option>
                <option value="festivo">Festivo</option>
                <option value="deportivo">Deportivo</option>
                <option value="corporativo">Corporativo</option>
              </select>
            </div>
            <div className="col-span-12 sm:col-span-3 flex flex-col gap-1">
              <label className="text-[10px] text-on-surface-variant uppercase font-bold">Impacto</label>
              <select
                className="w-full px-4 py-2 bg-surface-container border border-outline-variant focus:outline-none focus:border-primary transition-colors font-body-md"
                value={form.impacto}
                onChange={(e) => setForm({ ...form, impacto: e.target.value })}
              >
                <option value="bajo">Bajo</option>
                <option value="medio">Medio</option>
                <option value="alto">Alto</option>
                <option value="critico">Crítico</option>
              </select>
            </div>
            <div className="col-span-12 sm:col-span-4 flex flex-col gap-1">
              <label className="text-[10px] text-on-surface-variant uppercase font-bold">Fecha inicio</label>
              <input
                type="date"
                className="w-full px-4 py-2 bg-surface-container border border-outline-variant focus:outline-none focus:border-primary transition-colors font-body-md"
                value={form.inicio}
                onChange={(e) => setForm({ ...form, inicio: e.target.value })}
                required
              />
            </div>
            <div className="col-span-12 sm:col-span-4 flex flex-col gap-1">
              <label className="text-[10px] text-on-surface-variant uppercase font-bold">Fecha fin</label>
              <input
                type="date"
                className="w-full px-4 py-2 bg-surface-container border border-outline-variant focus:outline-none focus:border-primary transition-colors font-body-md"
                value={form.fin}
                onChange={(e) => setForm({ ...form, fin: e.target.value })}
                required
              />
            </div>
            <div className="col-span-12 sm:col-span-4 flex items-end gap-2">
              <button type="submit" disabled={saving} className="bg-primary text-on-primary px-6 py-2 font-label-md uppercase tracking-widest rounded-sm disabled:opacity-50">
                {saving ? "Guardando..." : "Guardar"}
              </button>
              <button type="button" onClick={() => setShowForm(false)} className="border border-on-surface text-on-surface px-6 py-2 font-label-md uppercase tracking-widest rounded-sm">
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Event List */}
      <div className="overflow-hidden bg-surface-container-lowest border border-outline-variant">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-container-high/50 border-b border-outline-variant">
                <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Evento</th>
                <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Tipo</th>
                <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Impacto</th>
                <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Inicio</th>
                <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Fin</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/30 font-data-tabular">
              {loading && <tr><td colSpan={5} className="px-6 py-8 text-center text-on-surface-variant">Cargando...</td></tr>}
              {error && <tr><td colSpan={5} className="px-6 py-8 text-center text-error">Error: {error}</td></tr>}
              {eventos && eventos.length === 0 && (
                <tr><td colSpan={5} className="px-6 py-8 text-center text-on-surface-variant">Sin eventos registrados.</td></tr>
              )}
              {eventos?.map((ev, i) => (
                <tr key={i} className="hover:bg-surface-container-low/30">
                  <td className="px-6 py-4 font-bold text-on-surface">{ev.nombre}</td>
                  <td className="px-6 py-4">{ev.tipo}</td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 rounded text-[11px] font-bold uppercase tracking-tighter ${
                      ev.impacto_estimado === "critico" ? "bg-error-container text-on-error-container" :
                      ev.impacto_estimado === "alto" ? "bg-error-container/60 text-on-error-container" :
                      ev.impacto_estimado === "medio" ? "bg-primary-fixed/60 text-on-primary-fixed" :
                      "bg-surface-container text-on-surface-variant"
                    }`}>
                      {ev.impacto_estimado}
                    </span>
                  </td>
                  <td className="px-6 py-4">{ev.fecha_inicio?.slice(0, 10)}</td>
                  <td className="px-6 py-4">{ev.fecha_fin?.slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
