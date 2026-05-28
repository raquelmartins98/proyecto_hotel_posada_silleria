import { useInsforgeQuery } from "../hooks/useInsforge";

export default function Tiempo() {
  const { data: registros, loading, error } = useInsforgeQuery(
    "SELECT fecha, temp_max, temp_min, precipitacion FROM public.tiempo_toledo ORDER BY fecha DESC LIMIT 14"
  );

  return (
    <div>
      <div className="mb-lg">
        <h2 className="font-headline-lg text-headline-lg text-on-surface">
          Tiempo en Toledo
        </h2>
        <p className="font-body-md text-body-md text-on-surface-variant mt-2">
          Datos meteorológicos históricos y pronósticos
        </p>
      </div>

      {/* Current Weather Card */}
      <div className="bento-grid mb-lg">
        <div className="col-span-12 lg:col-span-4 bg-surface-container-lowest border border-outline-variant p-md flex flex-col items-center justify-center min-h-[200px]">
          <span className="material-symbols-outlined text-[64px] text-primary-fixed-dim mb-2">
            wb_sunny
          </span>
          <p className="font-headline-lg text-headline-lg text-on-surface">— °C</p>
          <p className="font-body-md text-body-md text-on-surface-variant">Conecta a Insforge para ver datos en vivo</p>
        </div>

        <div className="col-span-12 lg:col-span-8 bg-surface-container-lowest border border-outline-variant p-md">
          <div className="flex items-center gap-2 mb-4">
            <span className="material-symbols-outlined text-on-surface-variant">history</span>
            <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">
              Registro últimos 14 días
            </span>
          </div>

          {loading && <p className="text-on-surface-variant">Cargando...</p>}
          {error && <p className="text-error">Error: {error}</p>}
          {registros && registros.length === 0 && (
            <p className="text-on-surface-variant">Sin datos meteorológicos disponibles.</p>
          )}

          {registros && registros.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-outline-variant">
                    <th className="px-4 py-3 font-label-md text-on-surface-variant uppercase tracking-wider">Fecha</th>
                    <th className="px-4 py-3 font-label-md text-on-surface-variant uppercase tracking-wider">T° Max</th>
                    <th className="px-4 py-3 font-label-md text-on-surface-variant uppercase tracking-wider">T° Min</th>
                    <th className="px-4 py-3 font-label-md text-on-surface-variant uppercase tracking-wider">Precipitación</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant/30 font-data-tabular">
                  {registros.map((r, i) => (
                    <tr key={i} className="hover:bg-surface-container-low/30">
                      <td className="px-4 py-3">{r.fecha?.slice(0, 10)}</td>
                      <td className="px-4 py-3">{r.temp_max}°C</td>
                      <td className="px-4 py-3">{r.temp_min}°C</td>
                      <td className="px-4 py-3">{r.precipitacion} mm</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
