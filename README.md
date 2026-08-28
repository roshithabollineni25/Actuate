# ResQMesh AI

> **"AI-Powered Emergency Coordination. Human-Verified Response."**

ResQMesh AI is a production-oriented emergency response and resource coordination platform. It integrates agentic intelligence, real-time geospatial routing, multimodal incident intake, and tactical mission dispatch with a strict Human-in-the-Loop (HITL) safety workflow.

---

## Architecture Overview

```
resqmesh-ai/
├── frontend/          # React 18, Vite, TypeScript, Tailwind CSS, React Leaflet
├── backend/           # FastAPI, SQLAlchemy 2.0, Pydantic v2, PostgreSQL/PostGIS ready
├── docs/              # System architecture and multi-agent documentation
├── .env.example       # Template environment configuration
├── .gitignore         # Root gitignore rules
└── README.md          # Project guide and quickstart
```

For detailed architectural and agentic specifications, see:
- [System Architecture](docs/architecture.md)
- [Agent Specifications](docs/agents_overview.md)

---

## User Roles

1. **Citizen (`CITIZEN`)**: Emergency SOS reporting (voice/text), live broadcast alerts, and safe evacuation zones.
2. **Emergency Coordinator / Admin (`ADMIN`)**: Emergency Operations Center (EOC) Command Dashboard, AI agent proposal verification queue, inventory monitoring, and operational overrides.
3. **Rescue Team (`RESCUE_TEAM`)**: Tactical Field HUD, real-time assigned mission orders, hazard turn-by-turn navigation, and in-flight telemetry updates.

---

## Agentic AI System

ResQMesh AI decouples tasks into 6 dedicated agents:
1. **Situation Understanding Agent**: Powered by Google Gemini (`gemini-3.7-flash`), extracts structured casualty and hazard telemetry from raw voice/text reports.
2. **Risk & Priority Agent**: Triage scoring, severity index, and risk radius calculation.
3. **Resource Matching Agent**: Constraint-based matching for response units, medical supplies, and rescue gear.
4. **Route Intelligence Agent**: Deterministic safe corridor pathfinding avoiding hazardous or flooded roads.
5. **Mission Coordination Agent**: Synthesizes end-to-end mission plans for coordinator approval.
6. **Continuous Replanning Agent**: Dynamic in-flight replanning triggered by environmental or status changes.

---

## Quickstart Guide

### Prerequisites
- **Node.js**: v18+ (tested on Node v24)
- **Python**: 3.11+ (tested on Python 3.12)
- **PostgreSQL / PostGIS** (Optional for Phase 1; defaults to SQLite for local development)

---

### Backend Setup

1. **Navigate to the backend directory**:
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux / macOS
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```

5. **Run the backend server**:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   API Docs available at: [http://localhost:8000/docs](http://localhost:8000/docs)  
   Health endpoint: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

6. **Run tests**:
   ```bash
   pytest
   ```

---

### Frontend Setup

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Configure environment variables (optional)**:
   ```bash
   cp .env.example .env
   ```

4. **Run the development server**:
   ```bash
   npm run dev
   ```
   Access the web app at: [http://localhost:5173](http://localhost:5173)

5. **Build for production**:
   ```bash
   npm run build
   ```

---

## Engineering Guidelines
- **Zero Secrets in Code**: All API keys and connection strings use environment variables.
- **Deterministic vs. Generative**: Generative models are reserved for unstructured understanding; life-critical routing and resource assignments are strictly deterministic.
- **Human-in-the-Loop**: All AI-generated rescue proposals require human operator verification before execution.
