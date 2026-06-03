import { SEVERITY_BG, SEVERITY_COLORS } from "../../types";

interface Props { severity: string; size?: "sm" | "md" | "lg"; }

export function SeverityBadge({ severity, size = "md" }: Props) {
  const sz = size === "sm" ? "text-xs px-2 py-0.5" : size === "lg" ? "text-sm px-3 py-1.5" : "text-xs px-2.5 py-1";
  const classes = SEVERITY_BG[severity] || "bg-gray-500/10 text-gray-400 border border-gray-500/30";
  const dot = SEVERITY_COLORS[severity] || "#94a3b8";
  return (
    <span className={`inline-flex items-center gap-1.5 rounded font-bold ${sz} ${classes}`}>
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: dot }} />
      {severity}
    </span>
  );
}
