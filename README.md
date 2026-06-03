# 🛡️ SurveillanceIQ

## Enterprise AI Surveillance Intelligence Platform

SurveillanceIQ is an AI-powered surveillance intelligence platform that transforms raw CCTV footage into actionable security intelligence using Computer Vision, Threat Analytics, Face Recognition, and Generative AI.

The system automatically detects people, tracks movement, identifies individuals, analyzes suspicious behaviour, generates threat scores, creates incident reports, and provides AI-generated security recommendations through a modern Security Operations Center (SOC) dashboard.

---
## Project Structure

```text
AI-Surveillance-Platform/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       └── endpoints/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── tasks/
│   │   ├── utils/
│   │   └── main.py
│   │
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── store/
│   │   ├── hooks/
│   │   ├── types/
│   │   └── App.tsx
│   │
│   ├── public/
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
│
├── ml/
│   ├── embeddings/
│   ├── models/
│   ├── init_face_registry.py
│   └── generate_synthetic_videos.py
│
├── data/
│   ├── annotations/
│   ├── sensor_events/
│   └── sample_data/
│
├── docs/
│   ├── architecture.png
│   ├── data_generation.md
│   └── screenshots/
│
├── docker-compose.yml
├── README.md
├── openapi.json
└── Makefile
```

### Directory Description

| Directory          | Purpose                                                       |
| ------------------ | ------------------------------------------------------------- |
| backend/           | FastAPI backend services, APIs, database, processing pipeline |
| frontend/          | React dashboard and user interface                            |
| ml/                | Computer vision models, embeddings, AI utilities              |
| data/              | Sample datasets, annotations, sensor events                   |
| docs/              | Architecture diagrams, screenshots, documentation             |
| openapi.json       | Exported API specification                                    |
| docker-compose.yml | Multi-container deployment configuration                      |
| README.md          | Project documentation and setup guide                         |

```
```

# 🚀 Features

## 🎯 Computer Vision Intelligence

* YOLOv8 Person Detection
* Multi-Object Tracking (ByteTrack)
* DeepFace Face Recognition
* Person Re-identification
* Unknown Person Detection
* Real-time Video Analytics

---

## 🚨 Threat Detection

The platform automatically detects:

* Restricted Zone Violations
* Loitering Behaviour
* Tailgating Events
* Crowd Formation
* Suspicious Activity
* Unknown Person Presence
* Identity Mismatch
* Abandoned Objects
* Unauthorized Access Attempts

---

## 🧠 AI Threat Analysis

Every event is analyzed using:

* Threat Scoring Engine
* Severity Classification
* Explainable AI Reasoning
* Incident Prioritization
* Risk Assessment

Severity Levels:

| Level | Description              |
| ----- | ------------------------ |
| L1    | Normal Activity          |
| L2    | Suspicious Activity      |
| L3    | Critical Security Threat |

---

## 🤖 Generative AI Integration

For every major incident the system generates:

* Incident Summary
* Threat Explanation
* Security Assessment
* Recommended Action
* Operator Guidance

Example:

> An unknown individual entered a restricted zone and remained for an extended period. Threat score: 0.91. Immediate security review is recommended.

---

# 🏗️ System Architecture

```text
Video Upload / RTSP Streams
            │
            ▼
     YOLOv8 Detection
            │
            ▼
     ByteTrack Tracking
            │
            ▼
   DeepFace Recognition
            │
            ▼
  Behaviour Analysis
            │
            ▼
  Event Detection Engine
            │
            ▼
   Threat Scoring Engine
            │
            ▼
      Gemini / OpenAI
            │
            ▼
      FastAPI Backend
            │
            ▼
      React Dashboard
```

---

# 📊 Dashboard Modules

## Security Operations Dashboard

Real-time monitoring dashboard showing:

* Total Events
* Critical Alerts
* Suspicious Events
* Active Persons
* Processed Videos
* Threat Analytics
* Security Status

---

## Video Intelligence Center

Features:

* Live Video Playback
* Dynamic Zone Overlays
* Event Timeline
* Threat Labels
* Tracking IDs
* Face Recognition Results
* Event Markers

---

## Events Center

Security analysts can view:

* Event Type
* Severity
* Zone
* Person
* Timestamp
* Threat Score
* AI Summary

Supported Filters:

* Severity
* Event Type
* Person
* Zone
* Date Range

---

## Person Intelligence Center

Displays:

* Face Snapshot
* Person Identity
* Confidence Score
* Last Seen
* Threat Level
* Event History

---

## Analytics Center

Provides:

* Event Distribution
* Threat Trends
* Zone Activity
* Person Statistics
* Alert Distribution
* Security Metrics

---

# 📍 Dynamic Zone Intelligence

Unlike traditional surveillance systems, zones are fully dynamic.

Supported Zones:

* Lobby
* Restricted Area
* Corridor
* Exit
* Storage Room
* Parking Area
* Custom Zones

Features:

* Video-specific zones
* Scenario-specific layouts
* Dynamic polygon rendering
* Occupancy tracking
* Zone violation detection

---

# 🛠️ Technology Stack

## Frontend

* React
* TypeScript
* Vite
* Tailwind CSS

## Backend

* FastAPI
* SQLAlchemy
* JWT Authentication

## Computer Vision

* YOLOv8
* ByteTrack
* OpenCV
* DeepFace

## AI

* Gemini
* OpenAI GPT
* Threat Scoring Engine

## Database

* SQLite
* Redis

## Background Processing

* Celery
* Redis



---

# 🔄 Processing Pipeline

When a video is uploaded:

```text
Upload Video
      │
      ▼
Person Detection
      │
      ▼
Object Tracking
      │
      ▼
Face Recognition
      │
      ▼
Zone Analysis
      │
      ▼
Threat Detection
      │
      ▼
Threat Scoring
      │
      ▼
AI Incident Summary
      │
      ▼
Dashboard Update
      │
      ▼
Report Generation
```

---

# 📄 Generated Outputs

The system automatically produces:

### Processed Video

```text
tracked_video_final.mp4
```

### Event Logs

```text
events.json
event_log.csv
```

### Reports

```text
incident_report.docx
incident_summaries.json
```

### Evidence

```text
event_snapshots/
```

---

# ⚡ Installation

## Clone Repository

```bash
git clone https://github.com/<your-username>/SurveillanceIQ.git
cd SurveillanceIQ
```

---

## Backend Setup

```bash
cd backend

pip install -r requirements.txt

python -m uvicorn app.main:app --reload
```

---

## Frontend Setup

```bash
cd frontend

npm install

npm run dev
```

---

## Access

Frontend:

```text
http://localhost:3000
```

Backend:

```text
http://localhost:8000
```

Swagger:

```text
http://localhost:8000/docs
```

---

# 🎯 Key Highlights

✅ End-to-End AI Surveillance Platform

✅ Real-Time Threat Detection

✅ Face Recognition

✅ Multi-Object Tracking

✅ Dynamic Zone Intelligence

✅ AI Incident Summaries

✅ Security Operations Dashboard

✅ Incident Report Generation

✅ Explainable AI

✅ Enterprise-Ready Architecture

---

# 🔮 Future Enhancements

* Multi-Camera Support
* RTSP Stream Monitoring
* Mobile Application
* PostgreSQL Deployment
* Heatmap Analytics
* Edge AI Deployment
* Cloud-Native Scaling

---

# 👨‍💻 Author

Developed as an Enterprise AI Surveillance Intelligence Platform combining Computer Vision, Security Analytics, Threat Intelligence, and Generative AI to assist modern Security Operations Centers (SOC).
