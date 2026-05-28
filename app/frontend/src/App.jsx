import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import DashboardLayout from "./layouts/DashboardLayout";
import Dashboard from "./pages/Dashboard";
import Reservas from "./pages/Reservas";
import Festividades from "./pages/Festividades";
import Tiempo from "./pages/Tiempo";
import Competencia from "./pages/Competencia";
import Costes from "./pages/Costes";
import Ocupacion from "./pages/Ocupacion";
import Prediccion from "./pages/Prediccion";
import Asistente from "./pages/Asistente";
import Configuracion from "./pages/Configuracion";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<DashboardLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="reservas" element={<Reservas />} />
          <Route path="festividades" element={<Festividades />} />
          <Route path="tiempo" element={<Tiempo />} />
          <Route path="competencia" element={<Competencia />} />
          <Route path="costes" element={<Costes />} />
          <Route path="ocupacion" element={<Ocupacion />} />
          <Route path="prediccion" element={<Prediccion />} />
          <Route path="asistente" element={<Asistente />} />
          <Route path="comparador" element={<Competencia />} />
          <Route path="configuracion" element={<Configuracion />} />
          {/* Redirigir rutas sin página al Dashboard */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
