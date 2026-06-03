import { useEffect } from "react";
import { AlertPanel } from "../components/alerts/AlertPanel";
import { useEventsStore } from "../store/eventsStore";
import { ReportDownload } from "../components/reports/ReportDownload";
import { ShieldAlert } from "lucide-react";

export function EventsPage() {
  const { fetch, total, events } = useEventsStore();

  useEffect(() => { fetch(); }, []);

  const l3 = events.filter((e) => e.severity === "L3").length;
  const unacked = events.filter((e) => !e.acknowledged).length;

  return (
    <div className="p-6 max-w-screen-xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <ShieldAlert className="text-blue-400" size={22} />
          <div>
            <h1 className="text-xl font-bold text-white">Events</h1>
            <p className="text-slate-400 text-sm">
              {total} total · {l3} critical · {unacked} unacknowledged
            </p>
          </div>
        </div>
        <ReportDownload />
      </div>
      <AlertPanel compact={false} />
    </div>
  );
}
