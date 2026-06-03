import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import type { SurveillanceEvent } from "../../types";
import { SEVERITY_COLORS } from "../../types";

interface Props { events: SurveillanceEvent[]; }

export function ThreatChart({ events }: Props) {
  const counts: Record<string, number> = { L1: 0, L2: 0, "L2+": 0, L3: 0 };
  events.forEach((e) => { if (counts[e.severity] !== undefined) counts[e.severity]++; });
  const data = Object.entries(counts).map(([sev, count]) => ({ sev, count }));

  return (
    <div className="bg-[#141c2e] border border-[#1e2d4a] rounded-xl p-5">
      <h3 className="text-sm font-semibold text-slate-300 mb-4">Event Distribution by Severity</h3>
      <ResponsiveContainer width="100%" height={160}>
        <BarChart data={data} barSize={32}>
          <XAxis dataKey="sev" tick={{ fill: "#94a3b8", fontSize: 12 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={{ background: "#0f1629", border: "1px solid #1e2d4a", borderRadius: 8 }}
            labelStyle={{ color: "#e2e8f0" }}
          />
          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
            {data.map((entry) => (
              <Cell key={entry.sev} fill={SEVERITY_COLORS[entry.sev] || "#94a3b8"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
