import { AlertTriangle, Shield, Eye, Activity } from "lucide-react";

interface Stats {
  total: number; l3: number; l2: number; acknowledged: number;
}

export function StatsCards({ stats }: { stats: Stats }) {
  const cards = [
    { label: "Total Events", value: stats.total, icon: Activity, color: "text-blue-400", bg: "bg-blue-500/10" },
    { label: "Critical (L3)", value: stats.l3, icon: AlertTriangle, color: "text-red-400", bg: "bg-red-500/10" },
    { label: "Suspicious (L2)", value: stats.l2, icon: Shield, color: "text-amber-400", bg: "bg-amber-500/10" },
    { label: "Acknowledged", value: stats.acknowledged, icon: Eye, color: "text-green-400", bg: "bg-green-500/10" },
  ];
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((c) => (
        <div key={c.label} className="bg-[#141c2e] border border-[#1e2d4a] rounded-xl p-5 flex items-center gap-4">
          <div className={`p-3 rounded-lg ${c.bg}`}>
            <c.icon className={c.color} size={22} />
          </div>
          <div>
            <div className="text-2xl font-bold text-white">{c.value}</div>
            <div className="text-xs text-slate-400">{c.label}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
