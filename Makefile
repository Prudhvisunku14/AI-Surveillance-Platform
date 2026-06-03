.PHONY: help setup data backend frontend docker test clean

help:
	@echo "SurveillanceIQ Platform — Available Commands"
	@echo "──────────────────────────────────────────────"
	@echo "  make setup      Install backend dependencies"
	@echo "  make data       Generate synthetic videos, sensors, face registry"
	@echo "  make backend    Start FastAPI backend (localhost:8000)"
	@echo "  make frontend   Start React frontend (localhost:3000)"
	@echo "  make docker     Start full platform via docker-compose"
	@echo "  make test       Run backend unit tests"
	@echo "  make clean      Remove generated data and DB"

setup:
	cd backend && pip install -r requirements.txt

data:
	cd backend && python ../ml/init_face_registry.py
	cd backend && python ../ml/generate_synthetic_videos.py
	cd backend && python ../ml/generate_sensor_data.py

backend:
	cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

frontend:
	cd frontend && npm install && npm run dev

docker:
	docker-compose up --build

test:
	cd backend && python -m pytest app/tests/ -v

clean:
	rm -f backend/surveillance.db
	rm -rf backend/frames/* backend/reports/* backend/logs/*
