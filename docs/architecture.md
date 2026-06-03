# SurveillanceIQ — System Architecture

## Overview

The SurveillanceIQ Platform is a layered, event-driven AI surveillance system.

```
Video Files / RTSP Streams
         |
  [Frame Extractor] ----------- [Sensor Ingestor]
         |                               |
  [Vision Intelligence Engine]    [Sensor Events DB]
  |- YOLOv8 Person Detection (conf=0.45)
  |- ByteTrack Multi-Object Tracking (re-ID after 30 frames)
  |- DeepFace FaceNet512 + FAISS (thresholds: 0.82 / 0.60)
  +- Behavioural Analysis
         |
  [Event Detection Engine] -- 15 event types, L1/L2/L2+/L3
         |
  [Threat Scoring Engine] -- 9-feature vector XGBoost
         |
  [GenAI Narrative Layer] -- GPT-4o + fallback
         |
  [FastAPI Backend] -- REST + WebSocket
         |
  [React Dashboard] -- Live overlays + Alerts + Reports
```

## Spec Compliance

### Detection
- YOLOv8n confidence threshold: 0.45 (spec section 6.2)

### Face Recognition Thresholds (spec section 7)
- Positive match: >= 0.82 cosine similarity
- Tentative: 0.60-0.82
- Unknown: < 0.60

### 15 Event Types (spec section 8)
person_detected, person_exited, identity_verified, identity_unknown,
loitering_warning, loitering_critical, zone_violation, tailgating_detected,
sensor_mismatch, identity_mismatch, crowd_alert, sudden_movement,
suspect_detected, abandoned_object, repeated_reappearance

### Threat Scoring (spec section 9)
Feature vector (9 features):
- identity_confidence, is_known_person, risk_level_encoded, zone_risk_encoded
- loitering_duration_norm (seconds/300, capped 1.0)
- sensor_corroborated, visit_count_1h_norm (count/10, capped 1.0)
- velocity_anomaly_score, concurrent_events_count

Severity: 0-0.30=L1, 0.31-0.60=L2, 0.61-0.80=L2+, 0.81-1.0=L3
Rule-based L3 overrides: suspect_detected, tailgating_detected,
abandoned_object, loitering_critical, identity_mismatch

### GenAI (spec section 10)
- Prompt: INCIDENT_SUMMARY_PROMPT (exact spec text)
- Outputs: incident_summary, classification_reasoning, recommended_action, confidence_note
- Graceful degradation: rule-based fallback when LLM unavailable

### Privacy (spec section 14)
1. Face Blur Mode (FACE_BLUR_MODE env)
2. Right to Erasure: DELETE /api/v1/persons/{id}
3. 30-day frame retention with automatic cleanup

### Database
- SQLite (SQLAlchemy async) for assignment
- PostgreSQL-ready (change DATABASE_URL)

### Auth (spec section 15, NFR)
- JWT HS256, 1-hour expiry
- Roles: Operator / Analyst / Admin
- Immutable audit log
