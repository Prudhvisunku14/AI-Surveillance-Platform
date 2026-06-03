import { useState } from "react";
import { ChevronDown, ChevronUp, Download, Check, Brain } from "lucide-react";
import type { SurveillanceEvent } from "../../types";
import { SeverityBadge } from "../shared/SeverityBadge";
import { useEventsStore } from "../../store/eventsStore";
import { downloadIncidentReport } from "../../services/api";
import { useAuthStore } from "../../store/authStore";

export function AlertCard({ event }: { event: SurveillanceEvent }) {
  const [expanded, setExpanded] = useState(false);
  const [ackName, setAckName] = useState("");
  const [acking, setAcking] = useState(false);
  const { acknowledge } = useEventsStore();
  const { user } = useAuthStore();

  const canAck = user?.role === "analyst" || user?.role === "admin";
  const genai = event.genai_data;
  const ts = new Date(event.timestamp).toLocaleTimeString();
  const explain = event.threat_explainability;

  async function handleAck() {
    const name = ackName || user?.full_name || "Analyst";
    setAcking(true);
    try { await acknowledge(event.event_id, name); } finally { setAcking(false); }
  }

  async function handleDownload() {
    await downloadIncidentReport(event.event_id);
  }

  const scoreColor =
    event.threat_score > 0.8 ? "#ef4444" :
    event.threat_score > 0.6 ? "#f97316" :
    event.threat_score > 0.3 ? "#f59e0b" : "#22c55e";

  return (
    <div
      className={`border rounded-xl overflow-hidden transition-all ${
        event.severity === "L3"
          ? "border-red-500/40 bg-red-500/5"
          : event.severity === "L2+"
          ? "border-orange-500/30 bg-orange-500/5"
          : "border-[#1e2d4a] bg-[#141c2e]"
      } ${event.acknowledged ? "opacity-60" : ""}`}
    >
      {/* Header */}
      <div
        className="p-4 flex items-center gap-3 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <SeverityBadge severity={event.severity} />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-white capitalize">
              {event.event_type.replace(/_/g, " ")}
            </span>
            {event.zone_id && (
              <span className="text-xs text-slate-500">Zone {event.zone_id}</span>
            )}
          </div>
          <div className="text-xs text-slate-400 mt-0.5">
            {ts}
            {event.persons_involved?.length > 0 && (
              <> · {event.persons_involved[0].display_name}</>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Threat score */}
          <div className="text-right">
            <div className="text-xs text-slate-500">Threat</div>
            <div className="text-sm font-bold" style={{ color: scoreColor }}>
              {(event.threat_score * 100).toFixed(0)}%
            </div>
          </div>

          {event.acknowledged ? (
            <Check size={16} className="text-green-400" />
          ) : (
            expanded ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />
          )}
        </div>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div className="border-t border-[#1e2d4a] p-4 space-y-4">
          {/* GenAI Summary */}
          {genai && (
            <div className="bg-[#0f1629] rounded-lg p-4 space-y-3">
              <div className="flex items-center gap-2 text-xs font-semibold text-blue-400 uppercase tracking-wider">
                <Brain size={12} /> AI Incident Analysis
              </div>
              <p className="text-sm text-slate-300 leading-relaxed">{genai.incident_summary}</p>
              <div>
                <div className="text-xs text-slate-500 mb-1">Classification Reasoning</div>
                <p className="text-xs text-slate-400">{genai.classification_reasoning}</p>
              </div>
              <div>
                <div className="text-xs text-slate-500 mb-1">Recommended Action</div>
                <p className="text-xs font-semibold text-amber-400">{genai.recommended_action}</p>
              </div>
              <div className="text-xs text-slate-600 italic">{genai.confidence_note}</div>
            </div>
          )}

          {/* Threat explainability */}
          {explain && (
            <div>
              <div className="text-xs text-slate-500 mb-2 uppercase tracking-wider">
                Threat Features (dominant: {explain.dominant_factor})
              </div>
              <div className="grid grid-cols-3 gap-1">
                {Object.entries(explain.feature_contributions).map(([k, v]) => (
                  <div key={k} className="bg-[#0f1629] rounded p-2">
                    <div className="text-xs text-slate-500 truncate">{k.replace(/_/g, " ")}</div>
                    <div className="text-xs font-bold text-white">{(v * 100).toFixed(1)}%</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Persons */}
          {event.persons_involved?.length > 0 && (
            <div>
              <div className="text-xs text-slate-500 mb-2 uppercase tracking-wider">Persons Involved</div>
              {event.persons_involved.map((p) => (
                <div key={p.track_id} className="flex items-center justify-between bg-[#0f1629] rounded p-2 mb-1">
                  <div>
                    <span className="text-sm text-white">{p.display_name}</span>
                    <span className="text-xs text-slate-500 ml-2">
                      Track #{p.track_id} · Conf: {(p.face_confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                  {p.duration_in_zone_seconds && (
                    <span className="text-xs text-slate-400">
                      {p.duration_in_zone_seconds.toFixed(0)}s in zone
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={handleDownload}
              className="flex items-center gap-2 px-3 py-2 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 text-xs rounded-lg transition-colors"
            >
              <Download size={12} /> Download DOCX
            </button>

            {!event.acknowledged && canAck && (
              <div className="flex items-center gap-2">
                <input
                  className="bg-[#0f1629] border border-[#1e2d4a] rounded px-2 py-1.5 text-xs text-white w-32 focus:outline-none focus:border-blue-500"
                  placeholder="Your name"
                  value={ackName}
                  onChange={(e) => setAckName(e.target.value)}
                />
                <button
                  onClick={handleAck}
                  disabled={acking}
                  className="flex items-center gap-1.5 px-3 py-2 bg-green-600/20 hover:bg-green-600/30 text-green-400 text-xs rounded-lg transition-colors disabled:opacity-50"
                >
                  <Check size={12} /> {acking ? "Saving..." : "Acknowledge"}
                </button>
              </div>
            )}

            {event.acknowledged && (
              <span className="text-xs text-green-400 flex items-center gap-1">
                <Check size={12} /> Acknowledged by {event.acknowledged_by}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
