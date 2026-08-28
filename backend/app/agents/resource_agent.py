"""Deterministic Resource Matching Agent."""

import math
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.incident import Incident
from app.models.rescue_team import (
    RescueTeam,
    TeamSpecialization,
    TeamStatus,
)
from app.models.resource import (
    Resource,
    ResourceStatus,
    ResourceType,
)


class ResourceMatchingAgent:
    """
    Deterministic resource and rescue-team matching agent.

    Matching is based on:
    - Team availability
    - Specialization compatibility
    - Team capacity
    - Geographic distance
    - Available inventory
    """

    def __init__(self):
        logger.info("Initialized ResourceMatchingAgent")

    @staticmethod
    def _distance_km(
        lat1: float,
        lng1: float,
        lat2: float,
        lng2: float,
    ) -> float:
        """Calculate great-circle distance using the Haversine formula."""

        earth_radius_km = 6371.0

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)

        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)

        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad)
            * math.cos(lat2_rad)
            * math.sin(delta_lng / 2) ** 2
        )

        return earth_radius_km * 2 * math.atan2(
            math.sqrt(a),
            math.sqrt(1 - a),
        )

    @staticmethod
    def _derive_requirements(
        incident: Incident,
    ) -> tuple[Optional[str], List[str]]:
        """
        Deterministically derive response requirements from incident category.
        """

        category = incident.category.value

        requirements = {
            "FLOOD": (
                TeamSpecialization.BOAT_RESCUE.value,
                [
                    ResourceType.LIFE_BOAT.value,
                    ResourceType.WATER_PUMP.value,
                ],
            ),
            "FIRE": (
                TeamSpecialization.GENERAL_RESPONSE.value,
                [
                    ResourceType.GENERATOR.value,
                ],
            ),
            "BUILDING_COLLAPSE": (
                TeamSpecialization.URBAN_SEARCH.value,
                [
                    ResourceType.OTHER.value,
                ],
            ),
            "MEDICAL_EMERGENCY": (
                TeamSpecialization.MEDICAL_EVAC.value,
                [
                    ResourceType.AMBULANCE.value,
                    ResourceType.MEDICAL_KIT.value,
                ],
            ),
            "TRAPPED_PERSONS": (
                TeamSpecialization.URBAN_SEARCH.value,
                [
                    ResourceType.DRONE.value,
                ],
            ),
            "HAZARDOUS_LEAK": (
                TeamSpecialization.GENERAL_RESPONSE.value,
                [
                    ResourceType.MEDICAL_KIT.value,
                ],
            ),
            "OTHER": (
                TeamSpecialization.GENERAL_RESPONSE.value,
                [],
            ),
        }

        return requirements.get(
            category,
            (
                TeamSpecialization.GENERAL_RESPONSE.value,
                [],
            ),
        )

    @staticmethod
    def _specialization_score(
        team: RescueTeam,
        required_specialization: Optional[str],
    ) -> float:
        """Return deterministic specialization compatibility score."""

        if not required_specialization:
            return 1.0

        if team.specialization.value == required_specialization:
            return 1.0

        if team.specialization.value == TeamSpecialization.GENERAL_RESPONSE.value:
            return 0.6

        return 0.0

    async def match_resources(
        self,
        incident_id: int,
        db: Session,
        required_specialization: Optional[str] = None,
        required_equipment: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Match available rescue teams and inventory to an incident.

        No synthetic assignments are created.
        All candidates come from the database.
        """

        incident = (
            db.query(Incident)
            .filter(Incident.id == incident_id)
            .first()
        )

        if not incident:
            raise ValueError(
                f"Incident {incident_id} was not found."
            )

        derived_specialization, derived_equipment = (
            self._derive_requirements(incident)
        )

        specialization = (
            required_specialization
            or derived_specialization
        )

        equipment = (
            required_equipment
            if required_equipment is not None
            else derived_equipment
        )

        # ---------------------------------------------------------
        # 1. Find available rescue teams
        # ---------------------------------------------------------

        teams = (
            db.query(RescueTeam)
            .filter(
                RescueTeam.status == TeamStatus.AVAILABLE
            )
            .all()
        )

        team_candidates = []

        required_capacity = max(
    incident.estimated_casualties or 1,
    1,
)

        for team in teams:
            if (
                team.current_lat is None
                or team.current_lng is None
            ):
                continue

            distance_km = self._distance_km(
                incident.latitude,
                incident.longitude,
                team.current_lat,
                team.current_lng,
            )

            specialization_score = self._specialization_score(
                team,
                specialization,
            )

            if specialization_score == 0:
                continue

            capacity_score = min(
                team.capacity / required_capacity,
                1.0,
            )

            # Distance score decreases as distance increases.
            distance_score = 1.0 / (1.0 + distance_km)

            readiness_score = (
                specialization_score * 0.45
                + capacity_score * 0.30
                + distance_score * 0.25
            )

            team_candidates.append(
                {
                    "team_id": team.id,
                    "team_name": team.team_name,
                    "specialization": team.specialization.value,
                    "status": team.status.value,
                    "availability": team.status.value,
                    "capacity": team.capacity,
                    "distance_km": round(distance_km, 3),
                    "distance": f"{round(distance_km, 2)} km",
                    "specialization_score": round(specialization_score, 3),
                    "capacity_score": round(capacity_score, 3),
                    "readiness_score": round(readiness_score, 3),
                    "match_score": round(readiness_score, 3),
                }
            )

        team_candidates.sort(
            key=lambda item: item["readiness_score"],
            reverse=True,
        )

        # ---------------------------------------------------------
        # 2. Find available resources
        # ---------------------------------------------------------

        resources = (
            db.query(Resource)
            .filter(
                Resource.status == ResourceStatus.AVAILABLE,
                Resource.available_quantity > 0,
            )
            .all()
        )

        resource_candidates = []

        for resource in resources:
            if not equipment:
                continue

            if resource.type.value not in equipment:
                continue

            distance_km = self._distance_km(
                incident.latitude,
                incident.longitude,
                resource.location_lat,
                resource.location_lng,
            )

            resource_candidates.append(
                {
                    "resource_id": resource.id,
                    "name": resource.name,
                    "type": resource.type.value,
                    "available_quantity": resource.available_quantity,
                    "depot_name": resource.depot_name,
                    "distance_km": round(
                        distance_km,
                        3,
                    ),
                }
            )

        resource_candidates.sort(
            key=lambda item: item["distance_km"]
        )

        # ---------------------------------------------------------
        # 3. Primary and backup allocation
        # ---------------------------------------------------------

        primary_team = (
            team_candidates[0]
            if team_candidates
            else None
        )

        backup_teams = (
            team_candidates[1:3]
            if len(team_candidates) > 1
            else []
        )

        allocation_status = "MATCH_FOUND"

        if primary_team is None:
            allocation_status = "NO_TEAM_AVAILABLE"

        # Categorized inventory breakdown for Section 5 requirements
        required_resources_list = []
        for eq_type in equipment:
            req_qty = max(incident.estimated_casualties or 1, 1) if eq_type in [ResourceType.LIFE_BOAT.value, ResourceType.AMBULANCE.value] else 2
            required_resources_list.append({
                "type": eq_type,
                "name": eq_type.replace("_", " ").title(),
                "required_quantity": req_qty,
            })

        all_db_resources = (
            db.query(Resource)
            .filter(Resource.status == ResourceStatus.AVAILABLE)
            .all()
        )
        available_resources_list = [
            {
                "resource_id": r.id,
                "name": r.name,
                "type": r.type.value,
                "available_quantity": r.available_quantity,
                "depot_name": r.depot_name,
            }
            for r in all_db_resources
        ]

        assigned_resources_list = []
        resource_shortages_list = []

        for req in required_resources_list:
            # Sum total available inventory across database depots for this canonical resource type
            total_avail = sum(r.available_quantity for r in all_db_resources if r.type.value == req["type"])
            # Never allocate more than actual available inventory
            assigned_qty = min(req["required_quantity"], total_avail)

            assigned_resources_list.append({
                "type": req["type"],
                "name": req["name"],
                "assigned_quantity": assigned_qty,
            })

            # Record shortage if required > available inventory
            if req["required_quantity"] > total_avail:
                resource_shortages_list.append({
                    "type": req["type"],
                    "name": req["name"],
                    "shortage_quantity": req["required_quantity"] - total_avail,
                })

        if resource_shortages_list:
            allocation_status = "PARTIAL_RESOURCE_SHORTAGE"

        return {
            "incident_id": incident.id,
            "allocation_status": allocation_status,
            "required_specialization": specialization,
            "required_equipment": equipment,
            "required_resources": required_resources_list,
            "available_resources": available_resources_list,
            "assigned_resources": assigned_resources_list,
            "resource_shortage": resource_shortages_list,
            "primary_team": primary_team,
            "backup_teams": backup_teams,
            "resource_matches": resource_candidates,
            "candidate_team_count": len(team_candidates),
            "candidate_resource_count": len(resource_candidates),
            "matching_method": {
                "algorithm": "deterministic_weighted_constraint_matching",
                "team_weights": {
                    "specialization": 0.45,
                    "capacity": 0.30,
                    "distance": 0.25,
                },
                "distance_metric": "haversine_km",
            },
        }