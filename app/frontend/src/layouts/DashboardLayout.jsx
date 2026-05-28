import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useInsforgeHealth } from "../hooks/useInsforge";

const NAV_ITEMS = [
  { label: "Dashboard", icon: "dashboard", path: "/" },
  { label: "Comparador de precios", icon: "monitoring", path: "/comparador" },
  { label: "Tiempo en Toledo", icon: "cloud", path: "/tiempo" },
  {
    label: "Festividades y eventos",
    icon: "calendar_today",
    path: "/festividades",
  },
  { label: "Reservas manuales", icon: "edit_calendar", path: "/reservas" },
  { label: "Costes reales", icon: "payments", path: "/costes" },
  {
    label: "Ocupación e incidencias",
    icon: "hotel_class",
    path: "/ocupacion",
  },
  { label: "Predicción de ocupación", icon: "show_chart", path: "/prediccion" },
  { label: "Asistente IA", icon: "smart_toy", path: "/asistente" },
  { label: "Configuración del hotel", icon: "settings", path: "/configuracion" },
];

function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-secondary border-r border-outline-variant flex flex-col z-50">
      {/* Logo / Brand */}
      <div className="px-6 py-8 mb-4">
        <h1 className="font-headline-md text-headline-md text-primary-fixed uppercase tracking-wider">
          POSADA SILLERÍA
        </h1>
        <p className="text-label-md text-secondary-fixed-dim uppercase tracking-widest mt-1 opacity-70">
          Toledo
        </p>
      </div>

      {/* Navegación */}
      <nav className="flex-1 px-2 space-y-1">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-sm transition-colors duration-200 ${
                isActive
                  ? "text-primary-fixed font-bold border-l-4 border-primary-fixed bg-on-secondary-fixed-variant/20"
                  : "text-secondary-fixed-dim hover:text-primary-fixed hover:bg-on-secondary-fixed-variant/10"
              }`
            }
          >
            <span className="material-symbols-outlined">{item.icon}</span>
            <span className="font-label-md text-label-md">
              {item.label}
            </span>
          </NavLink>
        ))}
      </nav>

      {/* Perfil de usuario */}
      <div className="px-6 py-4 flex items-center gap-3 border-t border-outline-variant/30">
        <div className="w-8 h-8 rounded-full bg-primary-fixed flex items-center justify-center text-primary overflow-hidden">
          <span className="material-symbols-outlined text-sm">person</span>
        </div>
        <div>
          <p className="font-label-md text-label-md text-primary-fixed font-bold">
            Admin Sillería
          </p>
          <p className="text-[10px] text-secondary-fixed-dim uppercase tracking-tighter">
            Gerente de Ingresos
          </p>
        </div>
      </div>
    </aside>
  );
}

function Header() {
  return (
    <header className="sticky top-0 z-40 bg-surface border-b border-outline-variant flex justify-between items-center px-margin-desktop py-sm w-full">
      {/* Buscador */}
      <div className="flex items-center flex-1 max-w-xl">
        <div className="relative w-full group">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant">
            search
          </span>
          <input
            type="text"
            placeholder="Buscar en el panel..."
            className="w-full pl-10 pr-4 py-2 bg-surface-container border border-outline-variant focus:outline-none focus:border-primary transition-colors font-body-md text-body-md rounded-sm"
          />
        </div>
      </div>

      {/* Acciones */}
      <div className="flex items-center gap-6">
        <button className="flex items-center gap-2 text-on-surface hover:bg-surface-container-high px-3 py-2 transition-colors active:scale-95 rounded-sm">
          <span className="material-symbols-outlined">calendar_month</span>
          <span className="font-label-md text-label-md hidden sm:inline">
            Calendario
          </span>
        </button>

        <button className="relative text-on-surface hover:bg-surface-container-high p-2 transition-colors active:scale-95 rounded-sm">
          <span className="material-symbols-outlined">notifications</span>
          <span className="absolute top-1 right-1 w-2 h-2 bg-error rounded-full"></span>
        </button>

        <div className="h-8 w-[1px] bg-outline-variant mx-2"></div>

        <div className="flex items-center gap-3">
          <span className="font-label-md text-label-md text-on-surface font-bold hidden sm:block">
            Posada Sillería
          </span>
          <div className="w-8 h-8 rounded-full border border-outline-variant overflow-hidden bg-surface-container-high flex items-center justify-center">
            <span className="material-symbols-outlined text-sm text-on-surface-variant">
              account_circle
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}

function RightPanel({ open, onToggle }) {
  const insforgeStatus = useInsforgeHealth();

  return (
    <>
      {/* Botón plegar/desplegar */}
      <button
        onClick={onToggle}
        className={`fixed top-1/2 -translate-y-1/2 z-40 w-6 h-12 bg-surface border border-outline-variant rounded-l-sm flex items-center justify-center hover:bg-surface-container transition-colors duration-300 hidden xl:flex ${
          open ? "right-72" : "right-0"
        }`}
        aria-label={open ? "Cerrar panel" : "Abrir panel"}
      >
        <span className="material-symbols-outlined text-sm transition-transform duration-300">
          {open ? "chevron_right" : "chevron_left"}
        </span>
      </button>

      {/* Panel deslizante */}
      <div
        className={`fixed right-0 top-0 h-full w-72 bg-surface border-l border-outline-variant p-md overflow-y-auto hidden xl:block transition-transform duration-300 ease-in-out z-30 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
      <h3 className="font-headline-md text-headline-md text-on-surface mb-4">
          Panel rápido
        </h3>

      {/* Estado Insforge */}
      <div className="bg-surface-container-lowest border border-outline-variant p-md mb-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="material-symbols-outlined text-sm text-on-surface-variant">
            database
          </span>
          <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">
            Estado API
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${
              insforgeStatus === "connected"
                ? "bg-success"
                : insforgeStatus === "checking"
                  ? "bg-primary-fixed-dim"
                  : "bg-error"
            }`}
          ></span>
          <span className="font-label-md text-label-md text-on-surface">
            Insforge{" "}
            {insforgeStatus === "connected"
              ? "Conectado"
              : insforgeStatus === "checking"
                ? "Verificando..."
                : "Desconectado"}
          </span>
        </div>
      </div>

      {/* Próximos eventos */}
      <div className="bg-surface-container-lowest border border-outline-variant p-md mb-4">
        <div className="flex items-center gap-2 mb-3">
          <span className="material-symbols-outlined text-sm text-on-surface-variant">
            event
          </span>
          <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">
            Próximos eventos
          </span>
        </div>
        <p className="font-body-md text-body-md text-on-surface-variant">
          No hay eventos próximos.
        </p>
      </div>

      {/* Ocupación rápida */}
      <div className="bg-surface-container-lowest border border-outline-variant p-md">
        <div className="flex items-center gap-2 mb-3">
          <span className="material-symbols-outlined text-sm text-on-surface-variant">
            hotel
          </span>
          <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">
            Hoy
          </span>
        </div>
        <p className="font-body-md text-body-md text-on-surface-variant">
          Conecta a Insforge para ver datos en vivo.
        </p>
      </div>
      </div>
    </>
  );
}

export default function DashboardLayout() {
  const location = useLocation();
  const isDashboard = location.pathname === "/";
  const [rightPanelOpen, setRightPanelOpen] = useState(isDashboard);
  const toggleRightPanel = () => setRightPanelOpen((prev) => !prev);

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <div
        className={`ml-64 min-h-screen transition-all duration-300 ease-in-out ${
          rightPanelOpen ? "xl:mr-72" : ""
        }`}
      >
        <Header />
        <main className="px-margin-desktop py-md">
          <Outlet />
        </main>
      </div>
      <RightPanel open={rightPanelOpen} onToggle={toggleRightPanel} />
    </div>
  );
}
