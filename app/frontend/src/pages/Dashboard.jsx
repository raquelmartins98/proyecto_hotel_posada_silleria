import { Link } from "react-router-dom";
import { useInsforgeQuery } from "../hooks/useInsforge";
import { healthCheck } from "../lib/insforge";
import { useEffect, useState } from "react";

const CARDS = [
  { title: "Comparador de precios", icon: "monitoring", path: "/comparador", desc: "Analiza tarifas, competencia y mercado en Toledo" },
  { title: "Tiempo en Toledo", icon: "cloud", path: "/tiempo", desc: "Condiciones meteorológicas actuales" },
  { title: "Festividades y eventos", icon: "calendar_today", path: "/festividades", desc: "Eventos locales y temporada alta" },
  { title: "Reservas manuales", icon: "edit_calendar", path: "/reservas", desc: "Gestiona reservas fuera de OTA" },
  { title: "Costes reales", icon: "payments", path: "/costes", desc: "Costes operativos mensuales" },
  { title: "Ocupación e incidencias", icon: "hotel_class", path: "/ocupacion", desc: "Ocupación histórica y anomalías" },
  { title: "Configuración del hotel", icon: "settings", path: "/configuracion", desc: "Habitaciones, temporadas, eventos" },
];

export default function Dashboard() {
  const { data: habitaciones } = useInsforgeQuery(
    "SELECT tipo, tarifa_base FROM public.habitaciones ORDER BY tarifa_base"
  );
  const [apiStatus, setApiStatus] = useState("checking");

  useEffect(() => {
    healthCheck().then((r) => setApiStatus(r.ok ? "ok" : "error"));
  }, []);

  return (
    <div>
      {/* Page Header */}
      <div className="mb-lg">
        <h2 className="font-headline-lg text-headline-lg text-on-surface">
          Panel de Control
        </h2>
        <p className="font-body-md text-body-md text-on-surface-variant mt-2">
          Resumen ejecutivo del Hotel Boutique Posada de la Sillería
        </p>
      </div>

      {/* Status + Quick Stats */}
      <div className="bento-grid mb-lg">
        <div className="col-span-12 lg:col-span-3 bg-surface-container-lowest border border-outline-variant p-md">
          <div className="flex items-center gap-2 mb-2">
            <span className={`w-2 h-2 rounded-full ${apiStatus === "ok" ? "bg-success" : apiStatus === "checking" ? "bg-primary-fixed-dim" : "bg-error"}`}></span>
            <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">Insforge API</span>
          </div>
          <p className="font-headline-md text-headline-md text-on-surface">
            {apiStatus === "ok" ? "Conectado" : apiStatus === "checking" ? "Verificando..." : "Desconectado"}
          </p>
        </div>

        <div className="col-span-12 lg:col-span-3 bg-surface-container-lowest border border-outline-variant p-md">
          <div className="flex items-center gap-2 mb-2">
            <span className="material-symbols-outlined text-sm text-on-surface-variant">bed</span>
            <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">Habitaciones</span>
          </div>
          <p className="font-headline-md text-headline-md text-on-surface">
            {habitaciones ? habitaciones.length : "—"}
          </p>
        </div>

        <div className="col-span-12 lg:col-span-3 bg-surface-container-lowest border border-outline-variant p-md">
          <div className="flex items-center gap-2 mb-2">
            <span className="material-symbols-outlined text-sm text-on-surface-variant">payments</span>
            <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">Ocupación media</span>
          </div>
          <p className="font-headline-md text-headline-md text-on-surface">—</p>
        </div>

        <div className="col-span-12 lg:col-span-3 bg-surface-container-lowest border border-outline-variant p-md">
          <div className="flex items-center gap-2 mb-2">
            <span className="material-symbols-outlined text-sm text-on-surface-variant">calendar_month</span>
            <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">Temporada actual</span>
          </div>
          <p className="font-headline-md text-headline-md text-on-surface">—</p>
        </div>
      </div>

      {/* Navigation Grid */}
      <h3 className="font-headline-md text-headline-md text-on-surface mb-4">
        Módulos del sistema
      </h3>
      <div className="bento-grid">
        {CARDS.map((card) => (
          <Link
            key={card.path}
            to={card.path}
            className="col-span-12 sm:col-span-6 lg:col-span-3 bg-surface-container-lowest border border-outline-variant p-md flex flex-col hover:bg-surface-container-low transition-colors duration-300 group"
          >
            <div className="flex items-center gap-3 mb-3">
              <span className="material-symbols-outlined text-primary text-2xl">
                {card.icon}
              </span>
              <h4 className="font-label-md text-label-md text-on-surface font-bold uppercase tracking-wider">
                {card.title}
              </h4>
            </div>
            <p className="font-body-md text-body-md text-on-surface-variant flex-1">
              {card.desc}
            </p>
            <span className="font-label-md text-label-md text-primary mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
              Acceder →
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
