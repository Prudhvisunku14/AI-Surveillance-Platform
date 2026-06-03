import { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "./store/authStore";
import { Navbar } from "./components/shared/Navbar";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { EventsPage } from "./pages/EventsPage";
import { VideosPage } from "./pages/VideosPage";
import { PersonsPage } from "./pages/PersonsPage";

function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const { user } = useAuthStore();
  if (!user) return <Navigate to="/login" replace />;
  return (
    <div className="min-h-screen bg-[#0a0e1a] flex flex-col">
      <Navbar />
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}

export default function App() {
  const { initialize } = useAuthStore();
  useEffect(() => { initialize(); }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<ProtectedLayout><DashboardPage /></ProtectedLayout>} />
        <Route path="/events" element={<ProtectedLayout><EventsPage /></ProtectedLayout>} />
        <Route path="/videos" element={<ProtectedLayout><VideosPage /></ProtectedLayout>} />
        <Route path="/persons" element={<ProtectedLayout><PersonsPage /></ProtectedLayout>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
