"""Mission coordination, human approval, dispatch, and lifecycle management."""

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.audit_log import AuditLog
from app.models.mission import Mission, MissionStatus
from app.models.rescue_team import RescueTeam, TeamStatus


class MissionCoordinationAgent:
    """Agent responsible for mission synthesis and HITL authorization."""

    def __init__(self):
        logger.info("Initialized MissionCoordinationAgent")

    async def synthesize_mission_proposal(
        self,
        db: Session,
        incident_id: int,
        situation_data: Dict[str, Any],
        risk_data: Dict[str, Any],
        resource_data: Dict[str, Any],
        route_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a PROPOSED mission from agent outputs."""

        rescue_team_id = resource_data.get("rescue_team_id")

        # ---------------------------------------------------------------
        # 1. DETERMINE MISSION PRIORITY
        # ---------------------------------------------------------------

        priority = risk_data.get(
            "triage_level",
            risk_data.get("urgency_level", "P2_URGENT"),
        )

        priority_mapping = {
            "CRITICAL": "P1_IMMEDIATE",
            "HIGH": "P2_URGENT",
            "MEDIUM": "P3_STANDARD",
            "LOW": "P4_MONITOR",
        }

        priority = priority_mapping.get(
            priority,
            priority
            if priority in {
                "P1_IMMEDIATE",
                "P2_URGENT",
                "P3_STANDARD",
                "P4_MONITOR",
            }
            else "P2_URGENT",
        )

        # ---------------------------------------------------------------
        # 2. NORMALIZE ROUTE DATA
        # ---------------------------------------------------------------

        route_polyline = route_data.get("route_polyline")

        if isinstance(route_polyline, list):
            route_polyline = json.dumps(route_polyline)

        eta_minutes = route_data.get("eta_minutes")

        # ---------------------------------------------------------------
        # 3. BUILD HUMAN-READABLE MISSION BRIEF
        # ---------------------------------------------------------------

        matched_hazards = risk_data.get("matched_hazards", [])

        if not isinstance(matched_hazards, list):
            matched_hazards = [str(matched_hazards)]

        mission_brief = (
            f"Emergency category: "
            f"{situation_data.get('category', 'OTHER')}. "
            f"Urgency: "
            f"{risk_data.get('triage_level', situation_data.get('urgency_level', 'MEDIUM'))}. "
            f"Hazards: "
            f"{', '.join(str(h) for h in matched_hazards) or 'None identified'}. "
            f"Estimated response time: "
            f"{eta_minutes if eta_minutes is not None else 'unknown'} minutes. "
            f"Safe route verified. Human approval required."
        )

        # ---------------------------------------------------------------
        # 4. PREVENT DUPLICATE ACTIVE MISSIONS
        # ---------------------------------------------------------------
        #
        # One incident should have only ONE active mission.
        #
        # This prevents repeated clicks on:
        #
        #     COORDINATE INCIDENT
        #
        # from creating Mission #3, Mission #4, Mission #5, etc.
        #
        # Existing active mission statuses:
        #
        #     PROPOSED
        #     APPROVED
        #     DISPATCHED
        #     EN_ROUTE
        #     ON_SCENE
        #
        # REJECTED / COMPLETED / ABORTED missions are not considered active.
        # ---------------------------------------------------------------

        mission = (
            db.query(Mission)
            .filter(
                Mission.incident_id == incident_id,
                Mission.status.in_(
                    [
                        MissionStatus.PROPOSED,
                        MissionStatus.APPROVED,
                        MissionStatus.DISPATCHED,
                        MissionStatus.EN_ROUTE,
                        MissionStatus.ON_SCENE,
                    ]
                ),
            )
            .order_by(Mission.created_at.desc())
            .first()
        )

        # ---------------------------------------------------------------
        # 5. CREATE MISSION ONLY IF NO ACTIVE MISSION EXISTS
        # ---------------------------------------------------------------

        if mission is None:
            mission = Mission(
                incident_id=incident_id,
                rescue_team_id=rescue_team_id,
                status=MissionStatus.PROPOSED,
                priority=priority,
                eta_minutes=eta_minutes,
                route_polyline=route_polyline,
                mission_brief=mission_brief,
            )

            db.add(mission)
            db.commit()
            db.refresh(mission)

            audit = AuditLog(
                agent_name="MissionCoordinationAgent",
                action="MISSION_PROPOSAL_SYNTHESIS",
                input_payload=json.dumps({
                    "incident_id": incident_id,
                    "situation_data": situation_data,
                    "risk_data": risk_data,
                    "resource_data": resource_data,
                }),
                output_payload=json.dumps({
                    "mission_id": mission.id,
                    "status": mission.status.value,
                    "rescue_team_id": mission.rescue_team_id,
                    "priority": mission.priority.value,
                }),
                human_verified=False,
                timestamp=datetime.now(timezone.utc),
            )
            db.add(audit)
            db.commit()

            logger.info(
                f"Created new mission {mission.id} "
                f"for incident {incident_id}"
            )

        else:
            # -----------------------------------------------------------
            # Existing active mission found.
            # Do NOT create a duplicate mission. Update PROPOSED details.
            # -----------------------------------------------------------
            if mission.status == MissionStatus.PROPOSED:
                mission.rescue_team_id = rescue_team_id
                mission.priority = priority
                mission.eta_minutes = eta_minutes
                mission.route_polyline = route_polyline
                mission.mission_brief = mission_brief
                db.commit()
                db.refresh(mission)

            logger.info(
                f"Reusing existing active mission {mission.id} "
                f"for incident {incident_id}. "
                f"Current status: {mission.status.value}"
            )

        # ---------------------------------------------------------------
        # 6. RETURN MISSION DATA
        # ---------------------------------------------------------------

        route_result = []

        if mission.route_polyline:
            try:
                route_result = json.loads(mission.route_polyline)
            except (json.JSONDecodeError, TypeError):
                route_result = mission.route_polyline

        return {
            "mission_id": mission.id,
            "incident_id": mission.incident_id,
            "rescue_team_id": mission.rescue_team_id,
            "status": mission.status.value,
            "priority": mission.priority.value,
            "eta_minutes": mission.eta_minutes,
            "route_polyline": route_result,
            "mission_brief": mission.mission_brief,
            "human_approval_required": True,
        }

    async def authorize_mission(
        self,
        db: Session,
        mission_id: int,
        coordinator_user_id: int,
        action: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Approve or reject a proposed mission with an audit record."""

        # ---------------------------------------------------------------
        # 1. LOAD MISSION
        # ---------------------------------------------------------------

        mission = (
            db.query(Mission)
            .filter(Mission.id == mission_id)
            .first()
        )

        if not mission:
            raise ValueError("Mission not found.")

        # ---------------------------------------------------------------
        # 2. ONLY PROPOSED MISSIONS CAN BE AUTHORIZED
        # ---------------------------------------------------------------

        if mission.status != MissionStatus.PROPOSED:
            raise ValueError(
                f"Mission cannot be authorized from status "
                f"{mission.status.value}."
            )

        # ---------------------------------------------------------------
        # 3. VALIDATE ACTION
        # ---------------------------------------------------------------

        action = action.upper()

        if action not in {"APPROVE", "REJECT"}:
            raise ValueError(
                "Action must be APPROVE or REJECT."
            )

        now = datetime.now(timezone.utc)

        # ---------------------------------------------------------------
        # 4. UPDATE MISSION AND INCIDENT STATUS
        # ---------------------------------------------------------------

        from app.models.incident import Incident, IncidentStatus

        incident = db.query(Incident).filter(Incident.id == mission.incident_id).first()

        if action == "APPROVE":
            mission.status = MissionStatus.APPROVED
            mission.approved_by = coordinator_user_id
            mission.approved_at = now
            if incident:
                incident.status = IncidentStatus.MISSION_PROPOSED

        elif action == "REJECT":
            mission.status = MissionStatus.REJECTED
            mission.approved_by = coordinator_user_id
            mission.approved_at = now
            if incident:
                incident.status = IncidentStatus.CANCELLED

            if mission.rescue_team_id:
                team = db.query(RescueTeam).filter(RescueTeam.id == mission.rescue_team_id).first()
                if team:
                    team.status = TeamStatus.AVAILABLE

        mission.updated_at = now

        # ---------------------------------------------------------------
        # 5. CREATE AUDIT LOG
        # ---------------------------------------------------------------

        audit = AuditLog(
            agent_name="MissionCoordinationAgent",
            action=f"MISSION_{action}",
            input_payload=json.dumps(
                {
                    "mission_id": mission_id,
                    "coordinator_user_id": coordinator_user_id,
                    "action": action,
                    "notes": notes,
                }
            ),
            output_payload=json.dumps(
                {
                    "mission_id": mission.id,
                    "status": mission.status.value,
                    "approved_by": mission.approved_by,
                    "approved_at": (
                        mission.approved_at.isoformat()
                        if mission.approved_at
                        else None
                    ),
                }
            ),
            human_verified=True,
            verified_by=coordinator_user_id,
            timestamp=now,
        )

        db.add(audit)
        db.commit()
        db.refresh(mission)

        logger.info(
            f"Mission {mission.id} {action}ED by coordinator "
            f"{coordinator_user_id}"
        )

        return {
            "mission_id": mission.id,
            "status": mission.status.value,
            "approved_by": mission.approved_by,
            "approved_at": (
                mission.approved_at.isoformat()
                if mission.approved_at
                else None
            ),
            "action": action,
            "notes": notes,
            "human_verified": True,
        }

    async def dispatch_mission(
        self,
        db: Session,
        mission_id: int,
        coordinator_user_id: int,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Dispatch an approved mission to its assigned rescue team."""

        # ---------------------------------------------------------------
        # 1. LOAD MISSION
        # ---------------------------------------------------------------

        mission = (
            db.query(Mission)
            .filter(Mission.id == mission_id)
            .first()
        )

        if not mission:
            raise ValueError("Mission not found.")

        # ---------------------------------------------------------------
        # 2. ONLY APPROVED MISSIONS CAN BE DISPATCHED
        # ---------------------------------------------------------------

        if mission.status != MissionStatus.APPROVED:
            raise ValueError(
                f"Mission cannot be dispatched from status "
                f"{mission.status.value}."
            )

        # ---------------------------------------------------------------
        # 3. RESCUE TEAM IS REQUIRED
        # ---------------------------------------------------------------

        if mission.rescue_team_id is None:
            raise ValueError(
                "Mission cannot be dispatched without "
                "an assigned rescue team."
            )

        now = datetime.now(timezone.utc)

        # ---------------------------------------------------------------
        # 4. MOVE MISSION TO DISPATCHED AND UPDATE INCIDENT STATUS
        # ---------------------------------------------------------------

        from app.models.incident import Incident, IncidentStatus

        mission.status = MissionStatus.DISPATCHED
        mission.updated_at = now

        if mission.incident_id:
            incident = db.query(Incident).filter(Incident.id == mission.incident_id).first()
            if incident:
                incident.status = IncidentStatus.IN_PROGRESS

        if mission.rescue_team_id:
            team = db.query(RescueTeam).filter(RescueTeam.id == mission.rescue_team_id).first()
            if team:
                team.status = TeamStatus.DEPLOYED

        # ---------------------------------------------------------------
        # 5. CREATE AUDIT RECORD
        # ---------------------------------------------------------------

        audit = AuditLog(
            agent_name="MissionCoordinationAgent",
            action="MISSION_DISPATCH",
            input_payload=json.dumps(
                {
                    "mission_id": mission_id,
                    "coordinator_user_id": coordinator_user_id,
                    "notes": notes,
                    "previous_status": MissionStatus.APPROVED.value,
                }
            ),
            output_payload=json.dumps(
                {
                    "mission_id": mission.id,
                    "status": mission.status.value,
                    "rescue_team_id": mission.rescue_team_id,
                    "dispatched_at": now.isoformat(),
                    "notes": notes,
                }
            ),
            human_verified=True,
            verified_by=coordinator_user_id,
            timestamp=now,
        )

        db.add(audit)
        db.commit()
        db.refresh(mission)

        logger.info(
            f"Mission {mission.id} DISPATCHED by coordinator "
            f"{coordinator_user_id} to rescue team "
            f"{mission.rescue_team_id}"
        )

        # ---------------------------------------------------------------
        # 6. RETURN DISPATCH RESULT
        # ---------------------------------------------------------------

        route_result = []

        if mission.route_polyline:
            try:
                route_result = json.loads(mission.route_polyline)
            except (json.JSONDecodeError, TypeError):
                route_result = mission.route_polyline

        return {
            "mission_id": mission.id,
            "status": mission.status.value,
            "rescue_team_id": mission.rescue_team_id,
            "eta_minutes": mission.eta_minutes,
            "route_polyline": route_result,
            "dispatched_by": coordinator_user_id,
            "dispatched_at": now.isoformat(),
            "notes": notes,
            "human_verified": True,
        }

    async def transition_mission(
        self,
        db: Session,
        mission_id: int,
        actor_user_id: int,
        actor_role: str,
        target_status: str,
        notes: Optional[str] = None,
        human_verified: bool = True,
    ) -> Dict[str, Any]:
        """Transition a dispatched mission through its field lifecycle."""

        # ---------------------------------------------------------------
        # 1. LOAD MISSION
        # ---------------------------------------------------------------

        mission = (
            db.query(Mission)
            .filter(Mission.id == mission_id)
            .first()
        )

        if not mission:
            raise ValueError("Mission not found.")

        current_status = mission.status

        # ---------------------------------------------------------------
        # 2. DEFINE ALLOWED FIELD TRANSITIONS
        # ---------------------------------------------------------------

        allowed_transitions = {
            MissionStatus.DISPATCHED: {
                MissionStatus.EN_ROUTE,
            },
            MissionStatus.EN_ROUTE: {
                MissionStatus.ON_SCENE,
            },
            MissionStatus.ON_SCENE: {
                MissionStatus.COMPLETED,
            },
        }

        # ---------------------------------------------------------------
        # 3. VALIDATE TARGET STATUS
        # ---------------------------------------------------------------

        try:
            target_status = MissionStatus(target_status.upper())
        except ValueError:
            raise ValueError(
                f"Invalid mission status: {target_status}"
            )

        # ---------------------------------------------------------------
        # 4. VALIDATE TRANSITION
        # ---------------------------------------------------------------

        if target_status not in allowed_transitions.get(
            current_status,
            set(),
        ):
            raise ValueError(
                f"Mission cannot transition from "
                f"{current_status.value} to {target_status.value}."
            )

        now = datetime.now(timezone.utc)

        # ---------------------------------------------------------------
        # 5. UPDATE STATUS
        # ---------------------------------------------------------------

        from app.models.incident import Incident, IncidentStatus

        mission.status = target_status
        mission.updated_at = now

        if mission.incident_id:
            incident = db.query(Incident).filter(Incident.id == mission.incident_id).first()
            if incident:
                if target_status == MissionStatus.COMPLETED:
                    incident.status = IncidentStatus.RESOLVED
                elif target_status in {MissionStatus.EN_ROUTE, MissionStatus.ON_SCENE, MissionStatus.DISPATCHED}:
                    incident.status = IncidentStatus.IN_PROGRESS

        if target_status == MissionStatus.COMPLETED and mission.rescue_team_id:
            team = db.query(RescueTeam).filter(RescueTeam.id == mission.rescue_team_id).first()
            if team:
                team.status = TeamStatus.AVAILABLE

        # ---------------------------------------------------------------
        # 6. CREATE AUDIT RECORD
        # ---------------------------------------------------------------

        audit = AuditLog(
            agent_name="MissionCoordinationAgent",
            action="MISSION_STATUS_TRANSITION",
            input_payload=json.dumps(
                {
                    "mission_id": mission_id,
                    "actor_user_id": actor_user_id,
                    "actor_role": actor_role,
                    "previous_status": current_status.value,
                    "target_status": target_status.value,
                    "notes": notes,
                }
            ),
            output_payload=json.dumps(
                {
                    "mission_id": mission.id,
                    "status": mission.status.value,
                    "updated_at": now.isoformat(),
                }
            ),
            human_verified=human_verified,
            verified_by=actor_user_id if human_verified else None,
            timestamp=now,
        )

        db.add(audit)
        db.commit()
        db.refresh(mission)

        logger.info(
            f"Mission {mission.id} transitioned from "
            f"{current_status.value} to {target_status.value} "
            f"by {actor_role} {actor_user_id}"
        )

        return {
            "mission_id": mission.id,
            "status": mission.status.value,
            "previous_status": current_status.value,
            "updated_at": now.isoformat(),
            "notes": notes,
            "human_verified": human_verified,
        }

    async def abort_mission(
        self,
        db: Session,
        mission_id: int,
        actor_user_id: int,
        actor_role: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Abort an active mission with an audit record."""
        mission = (
            db.query(Mission)
            .filter(Mission.id == mission_id)
            .first()
        )

        if not mission:
            raise ValueError("Mission not found.")

        current_status = mission.status

        if current_status in {MissionStatus.COMPLETED, MissionStatus.REJECTED, MissionStatus.ABORTED}:
            raise ValueError(f"Cannot abort mission in final state {current_status.value}.")

        now = datetime.now(timezone.utc)
        mission.status = MissionStatus.ABORTED
        mission.updated_at = now

        from app.models.incident import Incident, IncidentStatus
        incident = db.query(Incident).filter(Incident.id == mission.incident_id).first()
        if incident:
            incident.status = IncidentStatus.CANCELLED

        if mission.rescue_team_id:
            team = db.query(RescueTeam).filter(RescueTeam.id == mission.rescue_team_id).first()
            if team:
                team.status = TeamStatus.AVAILABLE

        audit = AuditLog(
            agent_name="MissionCoordinationAgent",
            action="MISSION_ABORT",
            input_payload=json.dumps(
                {
                    "mission_id": mission_id,
                    "actor_user_id": actor_user_id,
                    "actor_role": actor_role,
                    "previous_status": current_status.value,
                    "notes": notes,
                }
            ),
            output_payload=json.dumps(
                {
                    "mission_id": mission.id,
                    "status": mission.status.value,
                    "updated_at": now.isoformat(),
                }
            ),
            human_verified=True,
            verified_by=actor_user_id,
            timestamp=now,
        )

        db.add(audit)
        db.commit()
        db.refresh(mission)

        logger.info(f"Mission {mission.id} ABORTED by {actor_role} {actor_user_id}")

        return {
            "mission_id": mission.id,
            "status": mission.status.value,
            "previous_status": current_status.value,
            "updated_at": now.isoformat(),
            "notes": notes,
            "human_verified": True,
        }