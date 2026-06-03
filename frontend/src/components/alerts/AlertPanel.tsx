import { useEffect } from "react";
import { AlertCard } from "./AlertCard";
import { useEventsStore } from "../../store/eventsStore";
import type { SurveillanceEvent } from "../../types";
import { exportEventsCsv } from "../../services/api";
import { Download, RefreshCw, Filter } from "lucide-react";

export function AlertPanel({ compact = false }: { compact?: boolean }) {
  const { events, liveEvents, filters, setFilter, clearFilters, fetch, isLoading } = useEventsStore();

  useEffect(() => { fetch(); }, []);

  const display = compact
    ? liveEvents.slice(0, 10)
    : events;

  const severities = ["", "L3", "L2+", "L2", "L1"];
  const eventTypes = [
    "", "suspect_detected", "tailgating_detected", "identity_mismatch",
    "loitering_critical", "loitering_warning", "zone_violation",
    "identity_unknown", "crowd_alert", "sudden_movement", "abandoned_object",
    "repeated_reappearance", "sensor_mismatch",
  ];

  return (
    <div className="flex flex-col h-full">
      {!compact && (
        <div className="flex items-center justify-between mb-4 gap-3 flex-wrap">
          <div className="flex items-center gap-2 flex-wrap">
            <Filter size={14} className="text-slate-400" />
            <select
              className="bg-[#141c2e] border border-[#1e2d4a] text-slate-300 text-xs rounded px-2 py-1.5 focus:outline-none"
              value={filters.severity || ""}
              onChange={(e) => setFilter("severity", e.target.value || undefined)}
            >
              {severities.map((s) => (
                <option key={s} value={s}>{s || "All Severities"}</option>
              ))}
            </select>
            <select
              className="bg-[#141c2e] border border-[#1e2d4a] text-slate-300 text-xs rounded px-2 py-1.5 focus:outline-none"
              value={filters.event_type || ""}
              onChange={(e) => setFilter("event_type", e.target.value || undefined)}
            >
              {eventTypes.map((t) => (
                <option key={t} value={t}>{t || "All Types"}</option>
              ))}
            </select>
            <select
              className="bg-[#141c2e] border border-[#1e2d4a] text-slate-300 text-xs rounded px-2 py-1.5 focus:outline-none"
              value={filters.acknowledged === undefined ? "" : String(filters.acknowledged)}
              onChange={(e) => setFilter("acknowledged", e.target.value === "" ? undefined : e.target.value === "true")}
            >
              <option value="">All Status</option>
              <option value="false">Unacknowledged</option>
              <option value="true">Acknowledged</option>
            </select>
            <button onClick={clearFilters} className="text-xs text-slate-500 hover:text-white transition-colors">
              Clear
            </button>
          </div>
          <div className="flex gap-2">
            <button
              onClick={fetch}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[#141c2e] border border-[#1e2d4a] text-slate-400 text-xs rounded-lg hover:text-white transition-colors"
            >
              <RefreshCw size={12} className={isLoading ? "animate-spin" : ""} /> Refresh
            </button>
            <button
              onClick={() => exportEventsCsv({ severity: filters.severity })}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600/20 text-blue-400 text-xs rounded-lg hover:bg-blue-600/30 transition-colors"
            >
              <Download size={12} /> Export CSV
            </button>
          </div>
        </div>
      )}

      <div className="overflow-y-auto space-y-2 flex-1">
        {display.length === 0 && (
          <div className="text-center text-slate-500 py-12 text-sm">
            {isLoading ? "Loading events..." : "No events match current filters"}
          </div>
        )}
        {display.map((ev: SurveillanceEvent) => (
          <AlertCard key={ev.event_id} event={ev} />
        ))}
      </div>

      {!compact && (
        <div className="pt-3 text-xs text-slate-500 border-t border-[#1e2d4a] mt-3">
          Showing {display.length} of {useEventsStore.getState().total} events
        </div>
      )}
    </div>
  );
}
