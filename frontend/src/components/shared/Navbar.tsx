import { ShieldCheck, Bell, LogOut, User } from "lucide-react";
import { useAuthStore } from "../../store/authStore";
import { useEventsStore } from "../../store/eventsStore";
import { Link, useLocation } from "react-router-dom";

export function Navbar() {
  const { user, logout } = useAuthStore();
  const liveEvents = useEventsStore((s) => s.liveEvents);
  const l3Count = liveEvents.filter((e) => e.severity === "L3" && !e.acknowledged).length;
  const loc = useLocation();

  const links = [
    { to: "/", label: "Dashboard" },
    { to: "/events", label: "Events" },
    { to: "/videos", label: "Videos" },
    { to: "/persons", label: "Persons" },
  ];

  return (
    <nav className="flex items-center justify-between px-6 py-3 border-b border-[#1e2d4a] bg-[#0f1629]">
      <div className="flex items-center gap-3">
        <ShieldCheck className="text-blue-400" size={24} />
        <span className="font-bold text-white text-lg tracking-tight">SurveillanceIQ</span>
        <span className="text-xs text-slate-500 ml-2">AI Platform</span>
      </div>

      <div className="flex items-center gap-1">
        {links.map((l) => (
          <Link
            key={l.to}
            to={l.to}
            className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
              loc.pathname === l.to
                ? "bg-blue-600/20 text-blue-400"
                : "text-slate-400 hover:text-white hover:bg-white/5"
            }`}
          >
            {l.label}
          </Link>
        ))}
      </div>

      <div className="flex items-center gap-4">
        {l3Count > 0 && (
          <div className="flex items-center gap-1 bg-red-500/20 text-red-400 px-3 py-1 rounded-full text-xs font-bold animate-pulse">
            <Bell size={12} />
            {l3Count} CRITICAL
          </div>
        )}
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <User size={16} />
          <span>{user?.full_name}</span>
          <span className="text-xs bg-blue-600/30 text-blue-400 px-2 py-0.5 rounded">
            {user?.role}
          </span>
        </div>
        <button onClick={logout} className="text-slate-500 hover:text-red-400 transition-colors">
          <LogOut size={18} />
        </button>
      </div>
    </nav>
  );
}
