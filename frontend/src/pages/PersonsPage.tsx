import { useEffect, useState } from "react";
import { listPersons, deletePerson } from "../services/api";
import type { Person } from "../types";
import { useAuthStore } from "../store/authStore";
import { Users, ShieldAlert, Trash2 } from "lucide-react";

export function PersonsPage() {
  const [persons, setPersons] = useState<Person[]>([]);
  const { user } = useAuthStore();

  async function load() {
    try { setPersons(await listPersons()); } catch {}
  }

  useEffect(() => { load(); }, []);

  async function handleDelete(id: string, name: string) {
    if (!confirm(`GDPR Right to Erasure: permanently delete all data for ${name}?`)) return;
    await deletePerson(id);
    await load();
  }

  const riskColor = (r: string) =>
    r === "High" ? "text-red-400" : r === "Medium" ? "text-amber-400" : "text-green-400";

  const catIcon = (c: string) =>
    c === "Suspect" ? "🔴" : c === "Visitor" ? "🟡" : c === "Unknown" ? "⚪" : "🟢";

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <Users className="text-blue-400" size={22} />
        <h1 className="text-xl font-bold text-white">Person Registry</h1>
        <span className="text-xs text-slate-500">{persons.length} identities</span>
      </div>

      <div className="grid gap-3">
        {persons.length === 0 && (
          <div className="text-center text-slate-500 py-12 bg-[#141c2e] rounded-xl border border-[#1e2d4a]">
            No persons registered
          </div>
        )}
        {persons.map((p) => (
          <div key={p.id} className="bg-[#141c2e] border border-[#1e2d4a] rounded-xl p-5">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-[#0f1629] border border-[#1e2d4a] flex items-center justify-center text-lg">
                  {catIcon(p.category)}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-white">{p.name}</span>
                    <span className="text-xs text-slate-500">{p.id}</span>
                    {p.watchlist && (
                      <span className="text-xs bg-red-500/20 text-red-400 px-1.5 py-0.5 rounded flex items-center gap-1">
                        <ShieldAlert size={10} /> Watchlist
                      </span>
                    )}
                  </div>
                  <div className="flex gap-3 mt-1 text-xs text-slate-400">
                    <span>{p.category}</span>
                    <span className={riskColor(p.risk_level)}>{p.risk_level} Risk</span>
                    <span>Zones: {p.access_zones}</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-4 text-xs text-slate-400">
                <div className="text-right">
                  <div>Visits (24h): <span className="text-white">{p.visit_count_24h}</span></div>
                  <div>Duration: <span className="text-white">{p.presence_duration_seconds}s</span></div>
                </div>
                {user?.role === "admin" && (
                  <button
                    onClick={() => handleDelete(p.id, p.name)}
                    className="text-slate-600 hover:text-red-400 transition-colors p-1.5 rounded hover:bg-red-500/10"
                    title="GDPR Right to Erasure"
                  >
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            </div>

            {p.confidence_trace && p.confidence_trace.length > 0 && (
              <div className="mt-3 pt-3 border-t border-[#1e2d4a] flex items-center gap-2">
                <span className="text-xs text-slate-500">Confidence trace:</span>
                <div className="flex gap-1">
                  {p.confidence_trace.slice(-10).map((c, i) => (
                    <div key={i} className="w-4 h-4 rounded-sm" style={{
                      background: c >= 0.82 ? "#22c55e" : c >= 0.6 ? "#f59e0b" : "#ef4444",
                      opacity: 0.5 + c * 0.5,
                    }} title={`${(c * 100).toFixed(0)}%`} />
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
