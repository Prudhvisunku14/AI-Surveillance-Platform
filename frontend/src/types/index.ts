// Spec canonical event schema + all TypeScript types

export interface PersonInvolved {
  track_id: number;
  person_id: string;
  display_name: string;
  face_confidence: number;
  zone_id?: string;
  duration_in_zone_seconds?: number;
  category?: string;
}

export interface ThreatFeatures {
  identity_confidence: number;
  is_known_person: number;
  risk_level_encoded: number;
  zone_risk_encoded: number;
  loitering_duration_norm: number;
  sensor_corroborated: number;
  visit_count_1h_norm: number;
  velocity_anomaly_score: number;
  concurrent_events_count: number;
}

export interface ThreatExplainability {
  score: number;
  feature_contributions: Record<string, number>;
  dominant_factor: string;
  color: string;
}

export interface GenAIOutput {
  incident_summary: string;
  classification_reasoning: string;
  recommended_action: string;
  confidence_note: string;
}

export interface SurveillanceEvent {
  event_id: string;
  video_id?: string;
  event_type: string;
  severity: Severity;
  timestamp: string;
  frame_index?: number;
  frame_snapshot_path?: string;
  persons_involved: PersonInvolved[];
  threat_score: number;
  threat_features?: ThreatFeatures;
  threat_explainability?: ThreatExplainability;
  genai_summary?: string;
  genai_data?: GenAIOutput;
  acknowledged: boolean;
  acknowledged_by?: string;
  acknowledged_at?: string;
  zone_id?: string;
}

export type Severity = "L1" | "L2" | "L2+" | "L3";

export const SEVERITY_COLORS: Record<string, string> = {
  L1: "#22c55e", L2: "#f59e0b", "L2+": "#f97316", L3: "#ef4444",
};

export const SEVERITY_BG: Record<string, string> = {
  L1: "bg-green-500/10 text-green-400 border border-green-500/30",
  L2: "bg-amber-500/10 text-amber-400 border border-amber-500/30",
  "L2+": "bg-orange-500/10 text-orange-400 border border-orange-500/30",
  L3: "bg-red-500/10 text-red-400 border border-red-500/30",
};

export interface Person {
  id: string;
  name: string;
  category: string;
  risk_level: string;
  access_zones: string;
  watchlist: boolean;
  visit_count_24h: number;
  first_seen?: string;
  last_seen?: string;
  presence_duration_seconds: number;
  confidence_trace?: number[];
}

export interface Video {
  id: string;
  original_name: string;
  scenario: string;
  status: string;
  progress: number;
  uploaded_at: string;
  duration_seconds?: number;
}

export interface UserInfo {
  username: string;
  role: string;
  full_name: string;
}

export interface EventsResponse {
  items: SurveillanceEvent[];
  total: number;
  page: number;
  page_size: number;
}
