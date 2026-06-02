# Ve Lyra — AI-Powered Surveillance Intelligence Platform

> **Take-Home Assignment · 5 Days · Confidential · May 2026**

---

## 1. Executive Summary

The SurveillanceIQ platform is an end-to-end, AI-first security product that transforms passive video feeds into active, explainable intelligence. By combining state-of-the-art computer vision, real-time threat scoring, and GenAI narration, this system empowers security teams to act on precise, context-rich insights rather than raw footage.

This repository is the complete product delivery for the take-home assignment. Every component is designed to be modular, observable, and production-ready from day one.

AI-first means every decision — from alert generation to dashboard ranking — is driven by AI inference, not rule-based heuristics alone. Humans validate and override; the AI reasons continuously.

---

## 2. Product Vision & Approach

Traditional surveillance relies on human operators watching many camera streams. SurveillanceIQ inverts that model:

- AI watches every frame
- AI detects people, identities, zones, and behaviours
- Humans review curated alerts and incident intelligence

### Core Pillars

- **Vision Intelligence**: Every frame is understood, not just recorded.
- **Predictive Threat Scoring**: Behavioural, identity, and sensor signals feed a calibrated threat model.
- **Generative AI Narration**: Structured events are converted into incident summaries, reasoning, and recommended actions.
- **Downloadable Intelligence**: Analysts can export incident reports as DOCX and events as CSV.

---

## 3. What This Project Delivers

1. Video processing for uploaded footage and sample streams.
2. Person detection, multi-object tracking, and re-identification.
3. Identity classification as Employee / Visitor / Suspect / Unknown.
4. Behavioural analysis for loitering, tailgating, crowd formation, erratic motion, and abandoned objects.
5. Severity-scored events at L1, L2, and L3.
6. LLM-driven incident summaries and operator guidance.
7. Real-time React dashboard with overlays, alert panels, and report downloads.
8. One-click DOCX and CSV export for incident reports and event logs.

---

## 4. Data Requirements & Generation Strategy

All data in this repository is synthetic or self-generated. The backend includes scripts for:

- `ml/init_face_registry.py` — seed face identity registry and embeddings
- `ml/generate_synthetic_videos.py` — generate synthetic surveillance video scenarios
- `ml/generate_sensor_data.py` — create time-aligned sensor events and anomaly patterns

### Face Registry

Minimum registry identities seeded by default:

| ID | Name | Category | Risk | Access Zones |
|----|------|----------|------|--------------|
| P001 | Alice Mercer | Employee | Low | Lobby, Lab A, Server Room |
| P002 | Bob Henley | Employee | Low | Lobby, Lab A |
| P003 | Carol Zhang | Visitor | Medium | Lobby only |
| P004 | Dave Rostov | Suspect | High | NONE |
| P005 | Unknown | Unknown | High | NONE |

Embeddings are generated using DeepFace / FaceNet512 and stored as NumPy `.npy` arrays.

### Sensor Data

Synthetic events are generated in alignment with scenarios such as:

- door open with no person visible
- tailgating during single badge swipe
- face scan mismatch between badge ID and video face
- motion in a closed zone
- repeated failed biometric scans before access

---

## 5. Architecture Overview

SurveillanceIQ follows a layered, event-driven architecture with single-responsibility components.

### Layers

- **Layer 1 — Ingestion**: video files and sensor streams enter the system.
- **Layer 2 — Vision Intelligence Engine**: YOLO person detection → ByteTrack tracking → DeepFace matching → behavioural analysis.
- **Layer 3 — Event Detection Engine**: structured observations become typed, severity-scored events.
- **Layer 4 — Threat Scoring Engine**: feature vector produces a calibrated threat probability.
- **Layer 5 — GenAI Narrative Layer**: events are narrated into incident summaries.
- **Layer 6 — Backend API**: FastAPI exposes REST and WebSocket APIs.
- **Layer 7 — Frontend Dashboard**: React SPA shows live alerts, video overlays, and report exports.

### Data Flow

```text
Video Files / RTSP Streams   Sensor Event Streams
           |                     |
    [Frame Extractor]       [Sensor Ingestor]
           |                     |
  [Vision Intelligence Engine]   |
      ├─ YOLOv8 Person Detection  |
      ├─ ByteTrack / MOT         |
      ├─ DeepFace Recognition    |
      └─ Behavioural Analysis    |
           |
  [Event Detection Engine]       |
           |
  [Threat Scoring Engine]        |
           |
  [GenAI Narrative Layer]        |
           |
  [FastAPI Backend] ------------> [React Dashboard]
```

See `docs/architecture.md` for full architecture detail.

---

## 6. Vision Intelligence Engine

The engine converts raw pixels into structured intelligence at every frame.

### Video Input Processing

A frame extractor decodes video at a configurable FPS, routes frames to the detection queue, and uses a bounded queue to avoid memory overload.

### Object & Person Detection

- **Model**: YOLOv8n
- **Detection threshold**: `0.45`
- Each detection returns a bounding box, class label, and confidence score.

### Tracking

- **Multi-object tracking** via ByteTrack-style association.
- Tracks maintain ID, first/last seen timestamps, bounding box history, and zone history.
- Lost tracks are re-identified after `30` frames using face match logic.

### Behavioural Analysis

- **Loitering**: duration thresholds at `120s` (L2) and `300s` (L3).
- **Tailgating**: multiple persons entering on a single access event.
- **Crowd formation**: occupancy above zone limit.
- **Sudden movement**: velocity exceeds expected context.
- **Abandoned object**: stationary object > `60s` after the person leaves.
- **Direction violation** and repeated appearance analysis.

### Zone Intelligence

Zones are polygon regions with risk class, occupancy limits, and allowed categories. Each active track is checked against zone rules per frame.

---

## 7. Face Recognition & Identity Intelligence

Face recognition is asynchronous and operates on cropped person regions every few frames.

- **Model**: FaceNet512 via DeepFace
- **Thresholds**:
  - Positive: `>= 0.82`
  - Tentative: `0.60–0.82`
  - Unknown: `< 0.60`
- **Vector store**: FAISS for fast nearest-neighbour search
- **Fallback**: RetinaFace detection when crop quality is poor
- **Anti-spoofing**: passive texture-based liveness checks

Identity intelligence outputs include classification, duration, presence, visit frequency, and confidence trace data.

---

## 8. Event Detection Engine

Events are generated from vision observations and sensor signals.

### Severity Levels

- **L1 Normal** — log-only expected activity
- **L2 Suspicious** — human review recommended
- **L3 Critical** — immediate response required

### Event Types

Implemented event taxonomy includes:
- `person_detected`
- `person_exited`
- `identity_verified`
- `identity_unknown`
- `loitering_warning`
- `loitering_critical`
- `zone_violation`
- `tailgating_detected`
- `sensor_mismatch`
- `identity_mismatch`
- `crowd_alert`
- `sudden_movement`
- `suspect_detected`
- `abandoned_object`
- `repeated_reappearance`

### Event Schema

Each event stores structured evidence, including frame index, track/person details, threat score, and GenAI summary data.

---

## 9. Threat Scoring & Risk Modeling

Threat score is a calibrated probability in `[0.0, 1.0]` using an explainable feature vector.

### Features

- `identity_confidence`
- `is_known_person`
- `risk_level_encoded`
- `zone_risk_encoded`
- `loitering_duration_norm`
- `sensor_corroborated`
- `visit_count_1h_norm`
- `velocity_anomaly_score`
- `concurrent_events_count`

### Severity Mapping

| Score | Severity | Color | Action |
|------|----------|-------|--------|
| 0.00-0.30 | L1 Normal | Green | Log only |
| 0.31-0.60 | L2 Suspicious | Amber | Alert + GenAI summary |
| 0.61-0.80 | L2+ High Suspicion | Orange | Alert + notification |
| 0.81-1.00 | L3 Critical | Red | Immediate alert + auto-lock |

### Rule-based Overrides

Certain events always escalate to L3, e.g. `suspect_detected`, `tailgating_detected`, `identity_mismatch`, `abandoned_object`, `loitering_critical`.

---

## 10. GenAI Integration Layer

The GenAI layer converts structured surveillance events into natural-language incident intelligence.

### Prompt Template

```python
INCIDENT_SUMMARY_PROMPT = """You are an expert security intelligence analyst.
Given the following structured surveillance event, produce a concise, professional incident report.
Event Data:{event_json}
Respond in JSON with exactly these fields:
- "incident_summary": 2-3 sentence plain-English description of the incident
- "classification_reasoning": chain-of-thought explanation for the severity level
- "recommended_action": specific, actionable guidance for the security operator
- "confidence_note": any caveats about AI confidence or data quality"""
```

### Output

The output is returned as structured JSON with:
- `incident_summary`
- `classification_reasoning`
- `recommended_action`
- `confidence_note`

The backend gracefully falls back to deterministic explanations if OpenAI is unavailable.

---

## 11. Backend API Design

The backend is a FastAPI app with JWT authentication and WebSocket streaming.

### Core Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/auth/token` | Login and obtain JWT |
| POST | `/api/v1/videos/upload` | Upload video for processing |
| POST | `/api/v1/videos/{id}/process` | Trigger processing pipeline |
| GET | `/api/v1/videos/{id}/status` | Get processing status |
| GET | `/api/v1/events` | List events with filters |
| GET | `/api/v1/events/{id}` | Fetch event details and GenAI summary |
| POST | `/api/v1/events/{id}/acknowledge` | Acknowledge alert |
| GET | `/api/v1/persons` | List tracked persons |
| GET | `/api/v1/persons/{id}/card` | Person intelligence card |
| POST | `/api/v1/faces/register` | Register a new face |
| POST | `/api/v1/sensor/ingest` | Bulk ingest sensor events |
| GET | `/api/v1/alerts/live` | WebSocket real-time alert stream |
| GET | `/api/v1/reports/incident/{id}` | Download DOCX incident report |
| GET | `/api/v1/reports/events/export` | Export event log as CSV |
| GET | `/api/v1/health` | Service health check |

### API Docs

Once running, API docs are available at:
- `http://localhost:8000/docs`

---

## 12. Frontend Dashboard

The React frontend is a real-time security operations dashboard with:

- HTML5 video player + overlay canvas for bounding boxes and track IDs
- Color-coded overlays: green = employee, amber = visitor, red = suspect/unknown
- Zone polygon overlays with live occupancy counts
- Live alert panel ordered by threat score
- Filters for severity, event type, person, date, and acknowledgement status
- Expandable GenAI incident summaries
- Acknowledge buttons with analyst capture
- Download buttons for DOCX incident reports and CSV event logs

---

## 13. Notifications & Alerting

The platform delivers alerts via:

- **WebSocket dashboard notifications** for all events ≥ L2
- **Browser push style alert cards** for L3-critical events
- **Immutable audit log** for all events and analyst actions

---

## 14. Privacy, Compliance & Ethics

Privacy and explainability are built in:

- **Data minimisation**: only person-containing frames are retained
- **Retention policy**: frame snapshots are kept for 30 days by default
- **Consent notice**: deployment should include visible monitoring notices
- **Role-based access**: Operator, Analyst, Admin roles supported
- **Audit logging**: login, acknowledge, export actions are logged
- **Right to erasure**: person records and embeddings can be deleted
- **Explainability**: every L2/L3 event includes a reasoning trace

---

## 15. Non-Functional Requirements

- **Performance**: target low-latency frame processing and API responses
- **Reliability**: vision pipeline remains available even if GenAI is offline
- **Scalability**: designed for multiple concurrent video streams
- **Security**: JWT auth, TLS-ready, secrets configurable via `.env`
- **Observability**: structured JSON logging with trace and correlation IDs
- **Maintainability**: modular service layers and unit-testable code

---

## 16. Technology Stack

| Layer | Technology | Why |
|-------|------------|-----|
| Vision Detection | YOLOv8 (Ultralytics) | fast, accurate Python API |
| Tracking | ByteTrack-style MOT | robust persistent IDs and occlusion handling |
| Face Recognition | DeepFace + FaceNet512 | plug-and-play embedding matching |
| Vector Search | FAISS | sub-ms nearest neighbour search |
| Threat Scoring | XGBoost / explainable model | calibrated and interpretable |
| GenAI | OpenAI GPT-4o | structured incident narration |
| Backend | FastAPI (Python 3.11+) | async, high-performance, OpenAPI docs |
| Task Queue | Celery + Redis | decoupled async processing |
| Database | SQLite (local demo) | simple time-series event store |
| Cache / PubSub | Redis | WebSocket pub/sub and queueing |
| Frontend | React + TypeScript + Vite | fast SPA experience |
| UI | Tailwind CSS | clean production-ready UI |
| Reports | python-docx + CSV | audit-ready export formats |
| Containerization | Docker Compose | reproducible local dev |

---

## 17. Deployment Architecture

A single `docker-compose.yml` brings up all services with one command.

Services:
- `backend` — FastAPI app
- `worker` — Celery worker for video, GenAI, and report tasks
- `frontend` — React dashboard
- `redis` — broker/cache/pubsub
- `flower` — Celery monitoring UI

### Start locally

```bash
git clone <repo>
cd surveillance_platform
cp .env.example .env
# Edit .env, add OPENAI_API_KEY if available

docker-compose up --build
```

### Access URLs

- Frontend: `http://localhost:3000`
- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Celery Flower: `http://localhost:5555`

---

## 18. Deliverables Included

- `backend/`, `frontend/`, `ml/`, `data/`, `docs/`, `docker-compose.yml`, `README.md`
- Synthetic data generation scripts and seeded demo data
- Working end-to-end pipeline: upload video → process → alert → report
- DOCX incident report generation and CSV event export
- Auto-generated FastAPI OpenAPI docs
- Architecture documentation in `docs/architecture.md`

---

## 19. Repository Structure

- `backend/` — FastAPI service, processing pipeline, Celery tasks
- `frontend/` — React dashboard and real-time UI
- `ml/` — data generation, face registry, embedding utilities
- `docs/` — architecture and system design notes
- `data/` — videos, annotations, synthetic sensor events
- `frames/` — processed frame evidence
- `reports/` — generated incident reports

---

## 20. Running the Project Locally

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ for local scripts
- `OPENAI_API_KEY` if you want GPT-4o GenAI summaries

### Setup

```bash
cd surveillance_platform
cp .env.example .env
# optionally edit .env values
```

### Generate demo assets

```bash
cd backend
python ml/init_face_registry.py
python ml/generate_synthetic_videos.py
python ml/generate_sensor_data.py
```

### Bring up services

```bash
docker-compose up --build
```

---

## 21. Environment Variables

See `.env.example` for the complete list. Key settings include:

- `APP_ENV`, `SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- `DATABASE_URL`, `MONGO_URI`, `REDIS_URL`
- `YOLO_MODEL_PATH`, `FACE_MODEL_BACKEND`, `FACE_SIMILARITY_THRESHOLD`
- `OPENAI_API_KEY`, `OPENAI_MODEL`, `GENAI_ENABLED`
- `FRAME_EXTRACTION_FPS`, `DETECTION_CONFIDENCE`, `LOITERING_THRESHOLD_SECONDS`
- `REPORT_OUTPUT_DIR`, `FRAME_EVIDENCE_DIR`, `FRAME_RETENTION_DAYS`

---

## 22. Testing

From the backend folder:

```bash
cd backend
pip install -r requirements.txt
pytest app/tests/ -v
```

---

## 23. Notes & Next Steps

This implementation is built to match the assignment's AI-first vision and modular architecture. The platform is ready for future extensions such as multi-camera RTSP support, PostgreSQL / TimescaleDB production storage, and enterprise identity management.
#   A I - S u r v e i l l a n c e - P l a t f o r m  
 