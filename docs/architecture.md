# ResQMesh AI — System Architecture

> **"AI-Powered Emergency Coordination. Human-Verified Response."**

ResQMesh AI is an autonomous, agentic disaster response and tactical resource dispatch platform. The platform ingests real-time emergency signals (voice, text, sensor alerts), analyzes situational gravity, calculates optimal safety routes, matches rescue assets, and submits mission plans for coordinator approval.

---

## 1. High-Level System Architecture

```
                                    +------------------------------+
                                    |     CITIZENS / SENSORS       |
                                    |  (Voice / Text SOS Reports)  |
                                    +--------------+---------------+
                                                   |
                                                   v
                                    +------------------------------+
                                    |       API GATEWAY (v1)       |
                                    |     FastAPI / WebSockets     |
                                    +--------------+---------------+
                                                   |
        +------------------------------------------+------------------------------------------+
        |                                          |                                          |
        v                                          v                                          v
+-------------------------------+      +-------------------------------+      +-------------------------------+
|    Situation Understanding    |      |       Risk / Priority         |      |      Resource Allocation      |
|             Agent             | ---> |            Agent              | ---> |            Agent              |
|  (Multimodal Speech & Text)   |      |   (Urgency & Radius Scoring)  |      |   (Skill & Asset Matcher)     |
+-------------------------------+      +-------------------------------+      +---------------+---------------+
                                                                                              |
        +-------------------------------------------------------------------------------------+
        v
+-------------------------------+      +-------------------------------+      +-------------------------------+
|      Route Intelligence       |      |      Mission Coordination     |      |    Continuous Replanning      |
|             Agent             | ---> |            Agent              | <--> |            Agent              |
| (OSM Isochrones & Avoidance)  |      |  (Plan Synthesis & Dispatch)  |      |  (Dynamic In-Flight Reroute)  |
+-------------------------------+      +---------------+---------------+      +-------------------------------+
                                                       |
                                                       v
                                       +-------------------------------+
                                       |     HUMAN-IN-THE-LOOP (EOC)   |
                                       |  (Coordinator Final Approval) |
                                       +---------------+---------------+
                                                       |
                                                       v
                                       +-------------------------------+
                                       |     RESCUE TEAM FIELD HUD     |
                                       |  (Tactical Mission Execution) |
                                       +-------------------------------+
```

---

## 2. Core Architectural Pillars

### 2.1 Separation of Concerns & Deterministic Safety
- **Generative AI** is used where semantic intelligence is required (e.g., speech-to-intent, casualty triage, ambiguous situational extraction).
- **Deterministic Algorithms** are strictly used for routing, geospatial calculations, and constraint optimization (OSM Dijkstra/A*, PostGIS spatial queries, linear resource assignment).
- **Human-in-the-Loop (HITL)** maintains authority over life-critical mission dispatches.

### 2.2 Security & Data Integrity
- Strict role-based access control (`CITIZEN`, `ADMIN`, `RESCUE_TEAM`).
- JWT-based authentication with stateless verification and immutable audit logging.
- Comprehensive audit trails for every agent decision with inputs, confidence metrics, and coordinator overrides.

### 2.3 PostGIS-Ready Spatial Engine
- Geospatial coordinates stored with spatial indices.
- Road network status tracking (`ACTIVE`, `FLOODED`, `BLOCKED`, `DEBRIS_RESTRICTED`).
- Dynamic geofencing for exclusion zones and incident clusters.

---

## 3. Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Frontend UI** | React 18, Vite, TypeScript, Tailwind CSS, Lucide React |
| **Mapping & Geospatial** | Leaflet, React-Leaflet, OpenStreetMap Tile Layers |
| **Backend API** | Python 3.11+, FastAPI, Pydantic v2, Uvicorn |
| **Data & Persistence** | PostgreSQL, PostGIS, SQLAlchemy 2.0 ORM, Alembic |
| **AI & Multimodal** | Google Gemini API (Configurable model, default: `gemini-3.7-flash`) |
| **Testing & Quality** | Pytest, HTTPX, ESLint, TypeScript Compiler |
