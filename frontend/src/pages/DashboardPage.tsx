import { useEffect, useState } from "react";
import { StatsCards } from "../components/dashboard/StatsCards";
import { ThreatChart } from "../components/dashboard/ThreatChart";
import { AlertPanel } from "../components/alerts/AlertPanel";
import { VideoPlayer } from "../components/player/VideoPlayer";
import { useEventsStore } from "../store/eventsStore";
import { useAuthStore } from "../store/authStore";
import { alertWS } from "../services/websocket";
import { listVideos, getHealth } from "../services/api";
import type { Video, SurveillanceEvent } from "../types";
import { ReportDownload } from "../components/reports/ReportDownload";
import { Activity, Wifi } from "lucide-react";

export function DashboardPage() {
  const { events, fetch, addLiveEvent } = useEventsStore();
  const { user } = useAuthStore();
  const [videos, setVideos] = useState<Video[]>([]);
  const [selectedVideo, setSelectedVideo] = useState<Video | undefined>();
  const [health, setHealth] = useState<Record<string, string>>({});
  const [wsConnected, setWsConnected] = useState(false);

  useEffect(() => {
    fetch();
    listVideos().then(setVideos).catch(() => {});
    getHealth().then(setHealth).catch(() => {});

    // Subscribe to live alerts
    const unsub = alertWS.onAlert((ev) => {
      addLiveEvent(ev as SurveillanceEvent);
      setWsConnected(true);
    });
    return unsub;
  }, []);

  const l3 = events.filter((e) => e.severity === "L3").length;
  const l2 = events.filter((e) => e.severity === "L2" || e.severity === "L2+").length;
  const acked = events.filter((e) => e.acknowledged).length;
  const liveCount = useEventsStore((s) => s.liveEvents.length);

  return (
    <div className="p-6 space-y-6 max-w-screen-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Intelligence Dashboard</h1>
          <p className="text-slate-400 text-sm">Welcome, {user?.full_name}</p>
        </div>
        <div className="flex items-center gap-3">
          <div className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border ${wsConnected ? "border-green-500/30 text-green-400" : "border-slate-500/30 text-slate-500"}`}>
            <Wifi size={10} />
            {wsConnected ? "Live" : "Connecting..."}
          </div>
          {liveCount > 0 && (
            <span className="text-xs bg-blue-600/20 text-blue-400 px-2 py-1 rounded-full">
              {liveCount} live alerts
            </span>
          )}
          <ReportDownload />
        </div>
      </div>

      {/* System health bar */}
      {Object.keys(health).length > 0 && (
        <div className="flex gap-3 flex-wrap">
          {Object.entries(health).map(([key, val]) => key !== "version" && (
            <div key={key} className="flex items-center gap-1.5 text-xs">
              <Activity size={10} className={val === "ok" || val === "enabled" ? "text-green-400" : "text-amber-400"} />
              <span className="text-slate-400 capitalize">{key}:</span>
              <span className={val === "ok" || val === "enabled" ? "text-green-400" : "text-amber-400"}>{val}</span>
            </div>
          ))}
        </div>
      )}

      {/* Stats */}
      <StatsCards stats={{ total: events.length, l3, l2, acknowledged: acked }} />

      {/* Main 3-col layout */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Left: Video + chart */}
        <div className="xl:col-span-2 space-y-4">
          {/* Video selector */}
          {videos.length > 0 && (
            <div className="flex gap-2 flex-wrap">
              {videos.map((v) => (
                <button key={v.id}
                  onClick={() => setSelectedVideo(v)}
                  className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
                    selectedVideo?.id === v.id
                      ? "border-blue-500 text-blue-400 bg-blue-500/10"
                      : "border-[#1e2d4a] text-slate-400 hover:border-blue-500/50"
                  }`}
                >
                  {v.original_name} ({v.status})
                </button>
              ))}
            </div>
          )}
          <VideoPlayer video={selectedVideo} />
          <ThreatChart events={events} />
        </div>

        {/* Right: Live alerts */}
        <div className="xl:col-span-1">
          <div className="bg-[#141c2e] border border-[#1e2d4a] rounded-xl p-4 h-full">
            <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              Live Alerts
            </h3>
            <AlertPanel compact={true} />
          </div>
        </div>
      </div>
    </div>
  );
}
