import { useEffect, useRef, useState } from "react";
import { Upload, Play, RefreshCw, CheckCircle, Clock, XCircle } from "lucide-react";
import { listVideos, uploadVideo, processVideo, getVideoStatus } from "../services/api";
import type { Video } from "../types";

export function VideosPage() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState<string | null>(null);
  const [scenario, setScenario] = useState("lobby_entry");
  const fileRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  async function load() {
    try { setVideos(await listVideos()); } catch {}
  }

  useEffect(() => {
    load();
    pollRef.current = setInterval(load, 5000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await uploadVideo(file, scenario);
      await load();
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function handleProcess(videoId: string) {
    setProcessing(videoId);
    try {
      await processVideo(videoId);
      await load();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      alert(err.response?.data?.detail || "Processing failed");
    } finally {
      setProcessing(null);
    }
  }

  const statusIcon = (s: string) =>
    s === "completed" ? <CheckCircle size={14} className="text-green-400" /> :
    s === "processing" ? <RefreshCw size={14} className="text-blue-400 animate-spin" /> :
    s === "failed" ? <XCircle size={14} className="text-red-400" /> :
    <Clock size={14} className="text-slate-400" />;

  const scenarios = ["lobby_entry", "corridor_loitering", "open_area", "custom"];

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-xl font-bold text-white mb-6">Video Management</h1>

      {/* Upload */}
      <div className="bg-[#141c2e] border border-[#1e2d4a] rounded-xl p-6 mb-6">
        <h2 className="text-sm font-semibold text-slate-300 mb-4">Upload Video</h2>
        <div className="flex gap-3 flex-wrap items-end">
          <div>
            <label className="text-xs text-slate-400 mb-1 block">Scenario</label>
            <select
              className="bg-[#0f1629] border border-[#1e2d4a] text-slate-300 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
              value={scenario}
              onChange={(e) => setScenario(e.target.value)}
            >
              {scenarios.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
            </select>
          </div>
          <label className={`flex items-center gap-2 px-4 py-2 rounded-lg cursor-pointer text-sm font-medium transition-colors ${uploading ? "bg-blue-600/30 text-blue-300 cursor-not-allowed" : "bg-blue-600 hover:bg-blue-700 text-white"}`}>
            <Upload size={14} />
            {uploading ? "Uploading..." : "Upload MP4"}
            <input ref={fileRef} type="file" accept="video/mp4,video/avi,video/*" className="hidden" onChange={handleUpload} disabled={uploading} />
          </label>
        </div>
        <p className="text-xs text-slate-500 mt-3">Supported: MP4, AVI, MOV. Processing runs YOLOv8 + ByteTrack + DeepFace on every video.</p>
      </div>

      {/* Video list */}
      <div className="space-y-3">
        {videos.length === 0 && (
          <div className="text-center text-slate-500 py-12 bg-[#141c2e] rounded-xl border border-[#1e2d4a]">
            No videos yet — upload one above
          </div>
        )}
        {videos.map((v) => (
          <div key={v.id} className="bg-[#141c2e] border border-[#1e2d4a] rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {statusIcon(v.status)}
                <div>
                  <div className="text-sm font-medium text-white">{v.original_name}</div>
                  <div className="text-xs text-slate-400">
                    {v.scenario} · {v.duration_seconds ? `${v.duration_seconds.toFixed(1)}s` : "—"} · {new Date(v.uploaded_at).toLocaleString()}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                {v.status === "processing" && (
                  <div className="text-xs text-blue-400">{v.progress}%</div>
                )}
                {v.status === "uploaded" && (
                  <button
                    onClick={() => handleProcess(v.id)}
                    disabled={processing === v.id}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-green-600/20 hover:bg-green-600/30 text-green-400 text-xs rounded-lg transition-colors disabled:opacity-50"
                  >
                    <Play size={12} /> {processing === v.id ? "Starting..." : "Process"}
                  </button>
                )}
                {v.status === "completed" && (
                  <span className="text-xs text-green-400">✓ Complete</span>
                )}
              </div>
            </div>
            {v.status === "processing" && (
              <div className="mt-3 h-1.5 bg-[#0f1629] rounded-full overflow-hidden">
                <div className="h-full bg-blue-500 rounded-full transition-all" style={{ width: `${v.progress}%` }} />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
