import { useMemo } from "react";
import { useInsforgeQuery } from "../hooks/useInsforge";
import {
  LineChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const ESCENARIOS = [
  {
    key: "pesimista",
    titulo: "Pesimista",
    campo: "ocupacion_pesimista",
    bg: "bg-error-container/40",
    border: "border-error/30",
    text: "text-error",
    icono: "trending_down",
  },
  {
    key: "realista",
    titulo: "Realista",
    campo: "ocupacion_realista",
    bg: "bg-tertiary-container/40",
    border: "border-tertiary/30",
    text: "text-tertiary",
    icono: "trending_flat",
  },
  {
    key: "optimista",
    titulo: "Optimista",
    campo: "ocupacion_optimista",
    bg: "bg-success-container/40",
    border: "border-success/30",
    text: "text-success",
    icono: "trending_up",
  },
];

export default function Prediccion() {
  const { data, loading, error } = useInsforgeQuery(
    "SELECT fecha, ocupacion_pesimista, ocupacion_realista, ocupacion_optimista FROM public.predicciones ORDER BY fecha ASC"
  );

  const medias = useMemo(() => {
    if (!data || data.length === 0) return null;
    return ESCENARIOS.map((esc) => {
      const suma = data.reduce((acc, row) => acc + Number(row[esc.campo] || 0), 0);
      return { ...esc, media: suma / data.length };
    });
  }, [data]);

  return (
    <div>
      {/* Header */}
      <div className="mb-lg">
        <h2 className="font-headline-lg text-headline-lg text-on-surface">
          Predicción de ocupación
        </h2>
        <p className="font-body-md text-body-md text-on-surface-variant mt-2">
          Previsión SARIMA a 30 días
        </p>
      </div>

      {/* Estado de carga / datos */}
      <div className="bg-surface-container-lowest border border-outline-variant p-md mb-lg">
        {loading && (
          <p className="font-body-md text-body-md text-on-surface-variant">
            Cargando predicciones...
          </p>
        )}

        {error && (
          <p className="font-body-md text-body-md text-error">
            Error: {error}
          </p>
        )}

        {!loading && !error && data && data.length > 0 && (
          <p className="font-body-md text-body-md text-on-surface">
            Cargadas {data.length} predicciones desde{" "}
            <span className="font-bold">
              {new Date(data[0].fecha + "T12:00:00").toLocaleDateString("es-ES", {
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
            </span>{" "}
            hasta{" "}
            <span className="font-bold">
              {new Date(data[data.length - 1].fecha + "T12:00:00").toLocaleDateString("es-ES", {
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
            </span>
            .
          </p>
        )}

        {!loading && !error && data && data.length === 0 && (
          <p className="font-body-md text-body-md text-on-surface-variant">
            No hay predicciones disponibles.
          </p>
        )}
      </div>

      {/* Tarjetas de media por escenario */}
      {!loading && !error && medias && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-md mb-lg">
          {medias.map((esc) => (
            <div
              key={esc.key}
              className={`${esc.bg} ${esc.border} border p-md flex flex-col items-center text-center`}
            >
              <span className={`material-symbols-outlined text-2xl ${esc.text} mb-2`}>
                {esc.icono}
              </span>
              <span className={`font-headline-xl text-headline-xl ${esc.text} font-bold`}>
                {esc.media.toFixed(1)}%
              </span>
              <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider mt-1">
                {esc.titulo}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Gráfica de evolución — Realista */}
      {!loading && !error && data && data.length > 0 && (
        <>
        <div className="bg-surface-container-lowest border border-outline-variant p-md">
          <h3 className="font-headline-md text-headline-md text-on-surface mb-4">
            Evolución de la ocupación prevista
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart
              data={data.map((row) => ({
                ...row,
                fechaLabel: new Date(row.fecha + "T12:00:00").toLocaleDateString("es-ES", {
                  day: "numeric",
                  month: "short",
                }),
              }))}
              margin={{ top: 8, right: 16, bottom: 8, left: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-outline-variant)" />
              <XAxis
                dataKey="fechaLabel"
                tick={{ fontSize: 11, fill: "var(--color-on-surface-variant)" }}
                axisLine={{ stroke: "var(--color-outline-variant)" }}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fontSize: 11, fill: "var(--color-on-surface-variant)" }}
                axisLine={{ stroke: "var(--color-outline-variant)" }}
                tickLine={false}
                tickFormatter={(v) => `${v}%`}
              />
              <Legend
                wrapperStyle={{ fontSize: "13px", paddingTop: "8px" }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--color-surface-container-high)",
                  border: "1px solid var(--color-outline-variant)",
                  borderRadius: "4px",
                  fontSize: "13px",
                }}
                labelStyle={{ color: "var(--color-on-surface)", fontWeight: 600 }}
                formatter={(value, name) => [`${Number(value).toFixed(1)}%`, name]}
              />
              {/* Sombreado del abanico de incertidumbre entre pesimista y optimista */}
              <Area
                type="monotone"
                dataKey="ocupacion_pesimista"
                stackId="uncertainty"
                fill="none"
                stroke="none"
              />
              <Area
                type="monotone"
                dataKey="ocupacion_optimista"
                stackId="uncertainty"
                fill="var(--color-tertiary-container)"
                fillOpacity={0.25}
                stroke="none"
              />
              <Line
                type="monotone"
                dataKey="ocupacion_pesimista"
                stroke="var(--color-error)"
                strokeWidth={2}
                dot={{ r: 3, fill: "var(--color-error)" }}
                activeDot={{ r: 5, fill: "var(--color-error)" }}
                name="Pesimista"
              />
              <Line
                type="monotone"
                dataKey="ocupacion_realista"
                stroke="var(--color-tertiary)"
                strokeWidth={2}
                dot={{ r: 3, fill: "var(--color-tertiary)" }}
                activeDot={{ r: 5, fill: "var(--color-tertiary)" }}
                name="Realista"
              />
              <Line
                type="monotone"
                dataKey="ocupacion_optimista"
                stroke="var(--color-success)"
                strokeWidth={2}
                dot={{ r: 3, fill: "var(--color-success)" }}
                activeDot={{ r: 5, fill: "var(--color-success)" }}
                name="Optimista"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Tabla de predicciones — 30 días */}
        <div className="mt-lg overflow-hidden bg-surface-container-lowest border border-outline-variant">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-surface-container-high/50 border-b border-outline-variant">
                  <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Fecha</th>
                  <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Pesimista</th>
                  <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Realista</th>
                  <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Optimista</th>
                  <th className="px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider">Recomendación</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/30 font-data-tabular">
                {data.map((row, i) => {
                  const realista = Number(row.ocupacion_realista);
                  let recomendacion, badgeClass;
                  if (realista > 75) {
                    recomendacion = "Subir tarifa";
                    badgeClass = "bg-success-container text-success";
                  } else if (realista >= 50) {
                    recomendacion = "Mantener";
                    badgeClass = "bg-tertiary-container text-tertiary";
                  } else {
                    recomendacion = "Oferta/promoción";
                    badgeClass = "bg-error-container text-error";
                  }
                  return (
                    <tr key={row.id ?? i} className="hover:bg-surface-container-low/30 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        {new Date(row.fecha + "T12:00:00").toLocaleDateString("es-ES", {
                          day: "numeric",
                          month: "short",
                        })}
                      </td>
                      <td className="px-6 py-4 font-data-tabular">{Number(row.ocupacion_pesimista).toFixed(1)}%</td>
                      <td className="px-6 py-4 font-semibold font-data-tabular">{realista.toFixed(1)}%</td>
                      <td className="px-6 py-4 font-data-tabular">{Number(row.ocupacion_optimista).toFixed(1)}%</td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded text-[11px] font-bold uppercase tracking-tighter ${badgeClass}`}>
                          {recomendacion}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
        </>
      )}
    </div>
  );
}
