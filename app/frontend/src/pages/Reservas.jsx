import { useState } from "react";
import { useInsforgeQuery, useInsforgeMutate } from "../hooks/useInsforge";

const initialForm = {
  cliente: "",
  fecha_entrada: "",
  fecha_salida: "",
  tipo_habitacion: "",
  num_huespedes: 1,
  canal: "Directo",
  email: "",
  telefono: "",
  notas: "",
};

export default function Reservas() {
  const { data: reservas, loading, error, refetch } = useInsforgeQuery(
    "SELECT * FROM public.reservas ORDER BY fecha_entrada DESC LIMIT 20"
  );
  const { data: habitaciones } = useInsforgeQuery(
    "SELECT tipo FROM public.habitaciones ORDER BY tarifa_base"
  );
  const { run: crearReserva, loading: saving, error: saveError, success } = useInsforgeMutate();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(initialForm);
  const [toast, setToast] = useState(null);

  const showToast = (msg, type) => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 4000);
  };

  const validate = () => {
    if (!form.cliente.trim()) return "El nombre del cliente es obligatorio";
    if (!form.fecha_entrada) return "La fecha de entrada es obligatoria";
    if (!form.fecha_salida) return "La fecha de salida es obligatoria";
    if (form.fecha_salida <= form.fecha_entrada) return "La fecha de salida debe ser posterior a la de entrada";
    if (!form.tipo_habitacion) return "Selecciona un tipo de habitación";
    if (form.num_huespedes < 1 || form.num_huespedes > 6) return "El número de huéspedes debe ser entre 1 y 6";
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const err = validate();
    if (err) { showToast(err, "error"); return; }

    try {
      await crearReserva(
        `INSERT INTO public.reservas
         (cliente, fecha_entrada, fecha_salida, tipo_habitacion, num_huespedes, canal, email, telefono, notas)
         VALUES ($1, $2::date, $3::date, $4, $5, $6, $7, $8, $9)`,
        [form.cliente, form.fecha_entrada, form.fecha_salida, form.tipo_habitacion,
         form.num_huespedes, form.canal, form.email, form.telefono, form.notas]
      );
      showToast("Reserva creada correctamente", "success");
      setShowForm(false);
      setForm(initialForm);
      refetch();
    } catch (e) {
      showToast(e.message, "error");
    }
  };

  return (
    <div>
      {/* Toast */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-6 py-3 rounded-sm shadow-lg font-label-md uppercase tracking-wider ${
          toast.type === "success" ? "bg-success text-on-primary" : "bg-error text-on-error"
        }`}>
          {toast.msg}
        </div>
      )}

      <div className="flex justify-between items-start mb-lg">
        <div>
          <h2 className="font-headline-lg text-headline-lg text-on-surface">Reservas manuales</h2>
          <p className="font-body-md text-body-md text-on-surface-variant mt-2">
            Gestiona reservas directas (teléfono, email, walk-in)
          </p>
        </div>
        <button onClick={() => setShowForm(!showForm)}
          className="bg-primary text-on-primary px-6 py-3 font-label-md uppercase tracking-widest flex items-center gap-2 rounded-sm">
          <span className="material-symbols-outlined">add</span>
          Nueva reserva
        </button>
      </div>

      {/* Form */}
      {showForm && (
        <div className="bg-surface-container-lowest border border-outline-variant p-md mb-6">
          <h3 className="font-headline-md text-headline-md text-on-surface mb-4">Registrar reserva directa</h3>
          {saveError && (
            <div className="bg-error-container border border-error text-on-error-container px-4 py-3 mb-4 font-body-md rounded-sm">{saveError}</div>
          )}
          <form onSubmit={handleSubmit} className="bento-grid">
            <div className="col-span-12 sm:col-span-6 flex flex-col gap-1">
              <label className="text-[10px] text-on-surface-variant uppercase font-bold">Cliente *</label>
              <input className="w-full px-4 py-2 bg-surface-container border border-outline-variant focus:outline-none focus:border-primary font-body-md"
                value={form.cliente} onChange={(e) => setForm({...form, cliente: e.target.value})} required />
            </div>
            <div className="col-span-12 sm:col-span-3 flex flex-col gap-1">
              <label className="text-[10px] text-on-surface-variant uppercase font-bold">Email</label>
              <input type="email" className="w-full px-4 py-2 bg-surface-container border border-outline-variant focus:outline-none focus:border-primary font-body-md"
                value={form.email} onChange={(e) => setForm({...form, email: e.target.value})} />
            </div>
            <div className="col-span-12 sm:col-span-3 flex flex-col gap-1">
              <label className="text-[10px] text-on-surface-variant uppercase font-bold">Teléfono</label>
              <input className="w-full px-4 py-2 bg-surface-container border border-outline-variant focus:outline-none focus:border-primary font-body-md"
                value={form.telefono} onChange={(e) => setForm({...form, telefono: e.target.value})} />
            </div>
            <div className="col-span-12 sm:col-span-3 flex flex-col gap-1">
              <label className="text-[10px] text-on-surface-variant uppercase font-bold">Fecha entrada *</label>
              <input type="date" className="w-full px-4 py-2 bg-surface-container border border-outline-variant focus:outline-none focus:border-primary font-body-md"
                value={form.fecha_entrada} onChange={(e) => setForm({...form, fecha_entrada: e.target.value})} required />
            </div>
            <div className="col-span-12 sm:col-span-3 flex flex-col gap-1">
              <label className="text-[10px] text-on-surface-variant uppercase font-bold">Fecha salida *</label>
              <input type="date" className="w-full px-4 py-2 bg-surface-container border border-outline-variant focus:outline-none focus:border-primary font-body-md"
                value={form.fecha_salida} onChange={(e) => setForm({...form, fecha_salida: e.target.value})} required />
            </div>
            <div className="col-span-12 sm:col-span-3 flex flex-col gap-1">
              <label className="text-[10px] text-on-surface-variant uppercase font-bold">Habitación *</label>
              <select className="w-full px-4 py-2 bg-surface-container border border-outline-variant focus:outline-none focus:border-primary font-body-md"
                value={form.tipo_habitacion} onChange={(e) => setForm({...form, tipo_habitacion: e.target.value})} required>
                <option value="">Seleccionar...</option>
                {habitaciones?.map((h, i) => <option key={i} value={h.tipo}>{h.tipo}</option>)}
              </select>
            </div>
            <div className="col-span-12 sm:col-span-3 flex flex-col gap-1">
              <label className="text-[10px] text-on-surface-variant uppercase font-bold">Huéspedes</label>
              <input type="number" min={1} max={6} className="w-full px-4 py-2 bg-surface-container border border-outline-variant focus:outline-none focus:border-primary font-body-md"
                value={form.num_huespedes} onChange={(e) => setForm({...form, num_huespedes: parseInt(e.target.value)})} />
            </div>
            <div className="col-span-12 sm:col-span-6 flex flex-col gap-1">
              <label className="text-[10px] text-on-surface-variant uppercase font-bold">Canal</label>
              <select className="w-full px-4 py-2 bg-surface-container border border-outline-variant focus:outline-none focus:border-primary font-body-md"
                value={form.canal} onChange={(e) => setForm({...form, canal: e.target.value})}>
                <option value="Directo">Directo (teléfono/email)</option>
                <option value="Booking">Booking.com</option>
                <option value="Expedia">Expedia</option>
                <option value="Walk-in">Walk-in</option>
              </select>
            </div>
            <div className="col-span-12 flex flex-col gap-1">
              <label className="text-[10px] text-on-surface-variant uppercase font-bold">Notas</label>
              <textarea rows={2} className="w-full px-4 py-2 bg-surface-container border border-outline-variant focus:outline-none focus:border-primary font-body-md resize-none"
                value={form.notas} onChange={(e) => setForm({...form, notas: e.target.value})} />
            </div>
            <div className="col-span-12 flex gap-2">
              <button type="submit" disabled={saving} className="bg-primary text-on-primary px-6 py-2 font-label-md uppercase tracking-widest rounded-sm disabled:opacity-50">
                {saving ? "Guardando..." : "Guardar reserva"}
              </button>
              <button type="button" onClick={() => setShowForm(false)} className="border border-on-surface text-on-surface px-6 py-2 font-label-md uppercase tracking-widest rounded-sm">
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Reservations Table */}
      <div className="overflow-hidden bg-surface-container-lowest border border-outline-variant">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-container-high/50 border-b border-outline-variant">
                <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Cliente</th>
                <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Entrada</th>
                <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Salida</th>
                <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Habitación</th>
                <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Huéspedes</th>
                <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Canal</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/30 font-data-tabular">
              {loading && <tr><td colSpan={6} className="px-6 py-8 text-center text-on-surface-variant">Cargando...</td></tr>}
              {error && <tr><td colSpan={6} className="px-6 py-8 text-center text-error">Error: {error}</td></tr>}
              {reservas && reservas.length === 0 && (
                <tr><td colSpan={6} className="px-6 py-8 text-center text-on-surface-variant">No hay reservas registradas.</td></tr>
              )}
              {reservas?.map((r, i) => (
                <tr key={i} className="hover:bg-surface-container-low/30">
                  <td className="px-6 py-4 font-bold text-on-surface">{r.cliente}</td>
                  <td className="px-6 py-4">{r.fecha_entrada?.slice(0, 10)}</td>
                  <td className="px-6 py-4">{r.fecha_salida?.slice(0, 10)}</td>
                  <td className="px-6 py-4">{r.tipo_habitacion}</td>
                  <td className="px-6 py-4">{r.num_huespedes}</td>
                  <td className="px-6 py-4">{r.canal}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
