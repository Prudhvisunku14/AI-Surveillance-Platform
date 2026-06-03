#!/bin/bash
# SurveillanceIQ — Local Development Startup Script
# Usage: bash start_local.sh
set -e
cd "$(dirname "$0")"

echo "══════════════════════════════════════════════"
echo " SurveillanceIQ Platform — Local Startup"
echo "══════════════════════════════════════════════"

# Check Python
python3 --version || { echo "❌ Python 3 not found"; exit 1; }

# Backend setup
echo ""
echo "📦 Installing backend dependencies..."
cd backend
pip install -r requirements.txt -q

# Generate data if missing
if [ ! -f "surveillance.db" ]; then
    echo ""
    echo "🎭 Initializing face registry..."
    python3 ../ml/init_face_registry.py

    echo "🎬 Generating synthetic videos..."
    python3 ../ml/generate_synthetic_videos.py

    echo "📡 Generating sensor data..."
    python3 ../ml/generate_sensor_data.py
fi

echo ""
echo "🚀 Starting FastAPI backend on http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo "   Health:   http://localhost:8000/api/v1/health"
echo ""
echo "Demo credentials: admin/admin123, analyst/analyst123, operator/operator123"
echo ""
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
