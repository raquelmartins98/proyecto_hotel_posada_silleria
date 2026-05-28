import { useState, useEffect, useMemo } from "react";
import { select } from "../lib/insforge";

// ── Mapeo tipos de habitación competencia → nuestras ──
const MAPA_HABITACIONES = {
  "Doble Boutique": { nuestra: "Doble Estándar", precio: 0 },
  Suite: { nuestra: "Sillería Deluxe", precio: 0 },
};

// ── Componente ─────────────────────────────────────────

export default function Competencia() {
  const [precios, setPrecios] = useState([]);
  const [habitaciones, setHabitaciones] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // ── Carga de datos ─────────────────────────────────

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      select("precios_competencia", {
        select: "hotel,tipo_habitacion,fecha,precio,fuente",
        order: "fecha.desc",
        limit: 100,
      }),
      select("habitaciones", {
        select: "tipo,tarifa_base",
        order: "tarifa_base.asc",
      }),
    ])
      .then(([p, h]) => {
        if (!cancelled) {
          setPrecios(p ?? []);
          setHabitaciones(h ?? []);
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

  // ── Mapa tarifas base de nuestras habitaciones ────

  const tarifasMap = useMemo(() => {
    const map = {};
    for (const h of habitaciones) {
      map[h.tipo] = Number(h.tarifa_base);
    }
    // Completar el mapeo con los precios reales
    if (map["Doble Estándar"]) MAPA_HABITACIONES["Doble Boutique"].precio = map["Doble Estándar"];
    else if (map["Doble Superior"]) MAPA_HABITACIONES["Doble Boutique"].precio = map["Doble Superior"];
    if (map["Sillería Deluxe"]) MAPA_HABITACIONES["Suite"].precio = map["Sillería Deluxe"];
    else if (map["Junior Suite Heritage"]) MAPA_HABITACIONES["Suite"].precio = map["Junior Suite Heritage"];
    return map;
  }, [habitaciones]);

  // ── Calcular diferencia vs precio de Posada ───────

  const diffVsPosada = (row) => {
    const mapeo = MAPA_HABITACIONES[row.tipo_habitacion];
    if (!mapeo || !mapeo.precio) return null;
    const diff = Number(row.precio) - mapeo.precio;
    return diff;
  };

  // ── Render ─────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="font-body-lg text-on-surface-variant">Cargando precios...</p>
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
      {/* Header */}
      <div className="mb-lg">
        <h2 className="font-headline-lg text-headline-lg text-on-surface">
          Comparador de precios
        </h2>
        <p className="font-body-md text-body-md text-on-surface-variant mt-2">
          Analiza tus tarifas frente al mercado y hoteles similares en Toledo
        </p>
      </div>

      {/* Barra de estado */}
      <div className="bg-surface-container-lowest border border-outline-variant p-md mb-lg flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-on-surface-variant">history</span>
          <div>
            <p className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">
              Estado del sistema
            </p>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              {precios.length > 0
                ? `${precios.length} registros sincronizados`
                : "Sin datos disponibles"}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="flex items-center gap-2 border border-outline-variant text-on-surface px-md py-2 font-label-md uppercase tracking-wider hover:bg-surface-container transition-colors"
        >
          <span className="material-symbols-outlined text-lg">refresh</span>
          Actualizar ahora
        </button>
      </div>

      {/* Filtros */}
      <div className="bg-surface-container border border-outline-variant p-sm flex flex-wrap items-center gap-4 mb-lg">
        <div className="flex items-center gap-3 bg-surface-container-lowest px-4 py-2 border border-outline-variant min-w-[200px]">
          <span className="material-symbols-outlined text-on-surface-variant">date_range</span>
          <div className="flex flex-col">
            <span className="text-[10px] text-on-surface-variant uppercase font-bold">Rango de fechas</span>
            <span className="font-label-md">
              {precios.length > 0
                ? `${new Date(precios[precios.length - 1]?.fecha + "T12:00:00").toLocaleDateString("es-ES", { day: "numeric", month: "short" })} - ${new Date(precios[0]?.fecha + "T12:00:00").toLocaleDateString("es-ES", { day: "numeric", month: "short", year: "numeric" })}`
                : "—"}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3 bg-surface-container-lowest px-4 py-2 border border-outline-variant min-w-[180px]">
          <span className="material-symbols-outlined text-on-surface-variant">bed</span>
          <div className="flex flex-col">
            <span className="text-[10px] text-on-surface-variant uppercase font-bold">Habitación</span>
            <span className="font-label-md">Todas</span>
          </div>
        </div>
        <div className="flex items-center gap-3 bg-surface-container-lowest px-4 py-2 border border-outline-variant min-w-[200px]">
          <span className="material-symbols-outlined text-on-surface-variant">apartment</span>
          <div className="flex flex-col">
            <span className="text-[10px] text-on-surface-variant uppercase font-bold">Competencia</span>
            <span className="font-label-md">Todos los hoteles</span>
          </div>
        </div>
        <button
          type="button"
          className="bg-primary text-on-primary px-6 py-3 font-label-md uppercase tracking-widest flex items-center gap-2 rounded-sm"
        >
          <span className="material-symbols-outlined">filter_list</span>
          Filtrar
        </button>
      </div>

      {/* Tabla */}
      <div className="overflow-hidden bg-surface-container-lowest border border-outline-variant">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-container-high/50 border-b border-outline-variant">
                <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Hotel</th>
                <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Habitación</th>
                <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Fecha</th>
                <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Precio (€)</th>
                <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Vs Posada Sillería</th>
                <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Fuente</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/30 font-data-tabular">
              {precios.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-on-surface-variant">
                    <div className="flex flex-col items-center gap-2">
                      <span className="material-symbols-outlined text-3xl text-on-surface-variant/50">database</span>
                      <p className="font-body-md">Sin datos de competencia</p>
                    </div>
                  </td>
                </tr>
              )}
              {precios.map((row, i) => {
                const diff = diffVsPosada(row);
                return (
                  <tr key={row.id ?? i} className="hover:bg-surface-container-low/30 transition-colors">
                    <td className="px-6 py-4 font-bold text-on-surface">{row.hotel}</td>
                    <td className="px-6 py-4">{row.tipo_habitacion}</td>
                    <td className="px-6 py-4">
                      {new Date(row.fecha + "T12:00:00").toLocaleDateString("es-ES", {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                      })}
                    </td>
                    <td className="px-6 py-4 font-semibold">{Number(row.precio).toFixed(0)} €</td>
                    <td className="px-6 py-4">
                      {diff != null ? (
                        <div className={`flex items-center gap-1 font-semibold ${
                          diff > 0 ? "text-error" : diff < 0 ? "text-success" : "text-on-surface"
                        }`}>
                          <span className="material-symbols-outlined text-base">
                            {diff > 0 ? "arrow_upward" : diff < 0 ? "arrow_downward" : "remove"}
                          </span>
                          <span>{diff > 0 ? "+" : ""}{diff.toFixed(0)} €</span>
                        </div>
                      ) : (
                        <span className="text-on-surface-variant/50">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 bg-surface-container rounded text-[11px] font-bold uppercase tracking-tighter">
                        {row.fuente}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Paginación */}
        <div className="px-6 py-4 border-t border-outline-variant flex justify-between items-center bg-surface-container-low/20">
          <span className="font-label-md text-label-md text-on-surface-variant">
            Mostrando {precios.length} {precios.length === 1 ? "entrada" : "entradas"}
          </span>
          <div className="flex gap-2">
            <button
              disabled
              className="p-2 border border-outline-variant hover:bg-surface-container transition-colors disabled:opacity-30 rounded-sm"
            >
              <span className="material-symbols-outlined text-lg">chevron_left</span>
            </button>
            <button
              disabled
              className="p-2 border border-outline-variant hover:bg-surface-container transition-colors disabled:opacity-30 rounded-sm"
            >
              <span className="material-symbols-outlined text-lg">chevron_right</span>
            </button>
          </div>
        </div>
      </div>

      {/* Upload (deshabilitado — próx. feature) */}
      <div className="mt-lg border-2 border-dashed border-outline-variant p-lg text-center bg-surface-container-low/30">
        <span className="material-symbols-outlined text-3xl text-on-surface-variant/50">cloud_upload</span>
        <p className="font-body-md text-body-md text-on-surface-variant mt-2">
          Arrastra aquí tu Excel o CSV con precios de competencia
        </p>
        <p className="font-body-sm text-body-sm text-on-surface-variant/70 mt-1">
          Formatos soportados: .xlsx, .csv, .numbers (Max 10MB)
        </p>
        <button
          disabled
          className="mt-md border border-outline-variant text-on-surface-variant px-md py-2 font-label-md uppercase tracking-wider opacity-50 cursor-not-allowed"
        >
          Seleccionar archivo
        </button>
      </div>
    </div>
  );
}
