import axios from "axios";
import type { SurveillanceEvent, EventsResponse, Person, Video, UserInfo } from "../types";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

const api = axios.create({ baseURL: API_BASE });

// Inject JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-logout on 401
api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// ── Auth ──────────────────────────────────────────────────────────────
export async function login(username: string, password: string) {
  const form = new URLSearchParams();
  form.append("username", username);
  form.append("password", password);
  const { data } = await api.post("/auth/token", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return data;
}

export async function getMe(): Promise<UserInfo> {
  const { data } = await api.get("/auth/me");
  return data;
}

// ── Videos ────────────────────────────────────────────────────────────
export async function uploadVideo(file: File, scenario?: string) {
  const form = new FormData();
  form.append("file", file);
  if (scenario) form.append("scenario", scenario);
  const { data } = await api.post("/videos/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function processVideo(videoId: string) {
  const { data } = await api.post(`/videos/${videoId}/process`);
  return data;
}

export async function getVideoStatus(videoId: string) {
  const { data } = await api.get(`/videos/${videoId}/status`);
  return data;
}

export async function listVideos(): Promise<Video[]> {
  const { data } = await api.get("/videos");
  return data;
}

// ── Events ────────────────────────────────────────────────────────────
export async function listEvents(params: {
  severity?: string;
  event_type?: string;
  video_id?: string;
  acknowledged?: boolean;
  page?: number;
  page_size?: number;
  min_threat_score?: number;
}): Promise<EventsResponse> {
  const { data } = await api.get("/events", { params });
  return data;
}

export async function getEvent(eventId: string): Promise<SurveillanceEvent> {
  const { data } = await api.get(`/events/${eventId}`);
  return data;
}

export async function acknowledgeEvent(eventId: string, analystName: string) {
  const { data } = await api.post(`/events/${eventId}/acknowledge`, {
    analyst_name: analystName,
  });
  return data;
}

// ── Persons ───────────────────────────────────────────────────────────
export async function listPersons(): Promise<Person[]> {
  const { data } = await api.get("/persons");
  return data;
}

export async function getPersonCard(personId: string): Promise<Person> {
  const { data } = await api.get(`/persons/${personId}/card`);
  return data;
}

export async function deletePerson(personId: string) {
  const { data } = await api.delete(`/persons/${personId}`);
  return data;
}

// ── Sensors ───────────────────────────────────────────────────────────
export async function ingestSensorEvents(events: object[]) {
  const { data } = await api.post("/sensor/ingest", events);
  return data;
}

// ── Reports ───────────────────────────────────────────────────────────
export function getIncidentReportUrl(eventId: string) {
  const token = localStorage.getItem("access_token");
  return `${API_BASE}/reports/incident/${eventId}?token=${token}`;
}

export async function downloadIncidentReport(eventId: string) {
  const { data } = await api.get(`/reports/incident/${eventId}`, {
    responseType: "blob",
  });
  const url = URL.createObjectURL(new Blob([data]));
  const a = document.createElement("a");
  a.href = url;
  a.download = `incident_${eventId}.docx`;
  a.click();
  URL.revokeObjectURL(url);
}

export async function exportEventsCsv(params?: {
  severity?: string;
  video_id?: string;
  acknowledged?: boolean;
}) {
  const { data } = await api.get("/reports/events/export", {
    params,
    responseType: "blob",
  });
  const url = URL.createObjectURL(new Blob([data], { type: "text/csv" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = "events_export.csv";
  a.click();
  URL.revokeObjectURL(url);
}

// ── Health ────────────────────────────────────────────────────────────
export async function getHealth() {
  const { data } = await api.get("/health");
  return data;
}

export default api;
