# ResQMesh AI — Specialized Agent Architecture

ResQMesh AI employs a coordinated multi-agent system designed for emergency triage, routing, resource allocation, and mission lifecycle management.

---

## 1. Agent Overview & Responsibilities

### 1.1 Situation Understanding Agent (`situation_agent.py`)
- **Primary Role**: Multimodal data extraction from unstructured citizen reports (voice audio clips, emergency text messages, and sensor feeds).
- **Core Intelligence**: Powered by Google Gemini (`gemini-3.7-flash`).
- **Inputs**: Raw text, transcribed audio, caller metadata, optional photo attachments.
- **Outputs**: Standardized structured emergency payload (incident category, casualty count, trapped status, immediate hazards, landmark clues).

### 1.2 Risk & Priority Agent (`risk_agent.py`)
- **Primary Role**: Objective threat severity calculation, triage level assignment, and danger radius estimation.
- **Inputs**: Structured incident payload from Situation Agent, environmental weather telemetry, historical disaster risk metrics.
- **Outputs**: Urgency score (1–10), triage classification (`CRITICAL`, `HIGH`, `MODERATE`, `LOW`), computed impact polygon.

### 1.3 Resource Matching Agent (`resource_agent.py`)
- **Primary Role**: Constraint-satisfaction matching of nearby response units, medical supplies, search-and-rescue boats, drones, and heavy equipment.
- **Inputs**: Incident requirements, real-time rescue team rosters, available inventories, team capability tags.
- **Outputs**: Ranked candidate teams and inventory allocation proposals with readiness scores.

### 1.4 Route Intelligence Agent (`route_agent.py`)
- **Primary Role**: Safe corridor determination avoiding blocked roads, flooded lowlands, and active hazard zones.
- **Inputs**: Team coordinates, incident destination, live `RoadStatus` records, hazard exclusion boundaries.
- **Outputs**: Deterministic route geometry, estimated travel time (ETA), waypoint checkpoints, hazard proximity warnings.

### 1.5 Mission Coordination Agent (`mission_agent.py`)
- **Primary Role**: End-to-end mission synthesis compiling situation intelligence, matched team, allocated resources, and verified path into an actionable Mission Order.
- **Inputs**: Outputs from Agents 1–4.
- **Outputs**: Unified Mission Proposal presented to the Emergency Operations Center (EOC) coordinator for 1-click verification / modification.

### 1.6 Continuous Replanning Agent (`replanning_agent.py`)
- **Primary Role**: In-flight telemetry monitoring and dynamic rerouting.
- **Triggers**: Road status update (e.g. bridge collapse), incident severity escalation, or rescue unit delay.
- **Outputs**: Automated replan recommendations, live reroutes, and coordinator alerts.

---

## 2. Agent Execution Workflow

```
[Citizen SOS (Voice/Text)]
            │
            ▼
[Situation Understanding Agent]  ── (Gemini Multimodal Extraction)
            │
            ▼
   [Risk & Priority Agent]       ── (Triage Level & Severity Score)
            │
            ▼
 [Resource Matching Agent]       ── (Available Team & Gear Match)
            │
            ▼
  [Route Intelligence Agent]     ── (Safe Corridor & Road Avoidance)
            │
            ▼
 [Mission Coordination Agent]    ── (Unified Mission Proposal)
            │
            ▼
[Emergency Coordinator HITL]     ── (Approve / Override / Reject)
            │
            ▼
  [Field Rescue Team HUD]        ── (Live Execution & Replanning)
```
