import { useRef, useEffect, useState } from "react";
import { Play, Pause, SkipBack, SkipForward } from "lucide-react";
import type { Video } from "../../types";

/**
 * HTML5 video player with canvas overlay for bounding boxes and track IDs.
 * Spec: Green=employee, Amber=visitor, Red=suspect/unknown.
 * Zone polygon overlays with occupancy counter.
 * Pause, seek, frame-step controls.
 */

interface MockTrack {
  id: number;
  bbox: [number, number, number, number];
  label: string;
  category: "Employee" | "Visitor" | "Suspect" | "Unknown";
  confidence: number;
}

const CATEGORY_COLORS: Record<string, string> = {
  Employee: "#22c55e",
  Visitor: "#f59e0b",
  Suspect: "#ef4444",
  Unknown: "#ef4444",
};

const MOCK_ZONES = [
  { id: "Z02", name: "Restricted", points: [[0, 0], [300, 0], [300, 220], [0, 220]] as [number, number][], risk: "restricted", color: "rgba(239,68,68,0.15)" },
  { id: "Z01", name: "Lobby", points: [[40, 300], [560, 300], [560, 440], [40, 440]] as [number, number][], risk: "monitored", color: "rgba(34,197,94,0.1)" },
];

export function VideoPlayer({ video }: { video?: Video }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const frameRef = useRef<number>(0);

  // Demo tracks (in production populated from API events)
  const demoTracks: MockTrack[] = [
    { id: 1, bbox: [60, 60, 130, 200], label: "Alice (P001)", category: "Employee", confidence: 0.93 },
    { id: 2, bbox: [200, 80, 270, 200], label: "UNKNOWN", category: "Unknown", confidence: 0.31 },
    { id: 3, bbox: [350, 310, 420, 420], label: "Carol (P003)", category: "Visitor", confidence: 0.85 },
  ];

  function drawOverlay() {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const W = canvas.width;
    const H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    // Draw zones
    MOCK_ZONES.forEach((zone) => {
      ctx.beginPath();
      zone.points.forEach(([x, y], i) => {
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      });
      ctx.closePath();
      ctx.fillStyle = zone.color;
      ctx.fill();
      ctx.strokeStyle = zone.risk === "restricted" ? "#ef4444" : "#22c55e";
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 3]);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = zone.risk === "restricted" ? "#ef4444" : "#22c55e";
      ctx.font = "11px monospace";
      ctx.fillText(`${zone.id} ${zone.name}`, zone.points[0][0] + 4, zone.points[0][1] + 14);
    });

    // Draw person bounding boxes
    demoTracks.forEach((t) => {
      const color = CATEGORY_COLORS[t.category];
      const [x1, y1, x2, y2] = t.bbox;
      const w = x2 - x1;
      const h = y2 - y1;

      // Box
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.strokeRect(x1, y1, w, h);

      // Filled corners
      const cs = 10;
      ctx.fillStyle = color;
      [[x1, y1], [x2 - cs, y1], [x1, y2 - cs], [x2 - cs, y2 - cs]].forEach(([cx, cy]) => {
        ctx.fillRect(cx, cy, cs, 2);
        ctx.fillRect(cx, cy, 2, cs);
      });

      // Label bg
      const label = `#${t.id} ${t.label}`;
      ctx.font = "bold 10px monospace";
      const tw = ctx.measureText(label).width + 8;
      ctx.fillStyle = color;
      ctx.fillRect(x1, y1 - 18, tw, 18);
      ctx.fillStyle = "#000";
      ctx.fillText(label, x1 + 4, y1 - 4);

      // Confidence
      ctx.fillStyle = color;
      ctx.font = "9px monospace";
      ctx.fillText(`Conf: ${(t.confidence * 100).toFixed(0)}%`, x1, y2 + 12);
    });

    // Overlay info
    ctx.fillStyle = "rgba(0,0,0,0.5)";
    ctx.fillRect(0, H - 22, W, 22);
    ctx.fillStyle = "#94a3b8";
    ctx.font = "10px monospace";
    ctx.fillText(`SurveillanceIQ  |  Persons: ${demoTracks.length}  |  Zones: ${MOCK_ZONES.length}`, 8, H - 7);

    frameRef.current = requestAnimationFrame(drawOverlay);
  }

  useEffect(() => {
    frameRef.current = requestAnimationFrame(drawOverlay);
    return () => cancelAnimationFrame(frameRef.current);
  }, []);

  const togglePlay = () => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) { v.play(); setPlaying(true); }
    else { v.pause(); setPlaying(false); }
  };

  const stepFrame = (dir: number) => {
    const v = videoRef.current;
    if (!v) return;
    v.pause(); setPlaying(false);
    v.currentTime = Math.max(0, Math.min(v.duration, v.currentTime + dir / 25));
  };

  return (
    <div className="bg-[#141c2e] border border-[#1e2d4a] rounded-xl overflow-hidden">
      <div className="relative w-full bg-black" style={{ aspectRatio: "16/9" }}>
        {video ? (
          <video
            ref={videoRef}
            className="w-full h-full object-contain"
            src={`/api/v1/videos/${video.id}/stream`}
            onTimeUpdate={() => setCurrentTime(videoRef.current?.currentTime || 0)}
            onLoadedMetadata={() => setDuration(videoRef.current?.duration || 0)}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-slate-600 text-sm">
            No video selected — upload and process a video
          </div>
        )}
        <canvas
          ref={canvasRef}
          className="absolute inset-0 w-full h-full pointer-events-none"
          width={600}
          height={338}
        />
      </div>

      {/* Controls */}
      <div className="p-3 flex items-center gap-3">
        <button onClick={() => stepFrame(-1)} className="text-slate-400 hover:text-white transition-colors">
          <SkipBack size={16} />
        </button>
        <button onClick={togglePlay} className="text-white bg-blue-600 hover:bg-blue-700 rounded-full p-2 transition-colors">
          {playing ? <Pause size={14} /> : <Play size={14} />}
        </button>
        <button onClick={() => stepFrame(1)} className="text-slate-400 hover:text-white transition-colors">
          <SkipForward size={16} />
        </button>
        <input
          type="range" min={0} max={duration || 100} value={currentTime} step={0.04}
          onChange={(e) => { if (videoRef.current) videoRef.current.currentTime = Number(e.target.value); }}
          className="flex-1 h-1 accent-blue-500"
        />
        <span className="text-xs text-slate-500 font-mono">
          {currentTime.toFixed(1)}s / {duration.toFixed(1)}s
        </span>
      </div>

      {/* Legend */}
      <div className="px-3 pb-3 flex gap-3 text-xs">
        {["Employee", "Visitor", "Suspect / Unknown"].map((cat) => {
          const c = cat.includes("Suspect") ? "#ef4444" : cat === "Visitor" ? "#f59e0b" : "#22c55e";
          return (
            <span key={cat} className="flex items-center gap-1 text-slate-400">
              <span className="w-2 h-2 rounded-full" style={{ background: c }} />
              {cat}
            </span>
          );
        })}
      </div>
    </div>
  );
}
