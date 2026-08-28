"""Deterministic Risk and Priority Agent.

Calculates emergency threat, triage priority, casualty risk velocity,
environmental risk, and a danger perimeter from structured incident data.

Engineering rule:
- No LLM is used for risk scoring.
- Every score contribution is deterministic and auditable.
- The returned assessment includes a score breakdown and rationale.
"""

import math
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.logging import logger


class RiskPriorityAgent:
    """Deterministic emergency risk and triage assessment engine."""

    # Category severity contribution.
    CATEGORY_SEVERITY = {
        "BUILDING_COLLAPSE": 3.0,
        "FIRE": 3.0,
        "HAZARDOUS_LEAK": 3.0,
        "MEDICAL_EMERGENCY": 2.5,
        "TRAPPED_PERSONS": 3.0,
        "FLOOD": 2.5,
        "OTHER": 1.0,
    }

    # Explicit hazard contribution.
    HAZARD_SEVERITY = {
        "gas leak": 2.0,
        "fire": 2.0,
        "explosion": 2.0,
        "structural instability": 1.5,
        "flood": 1.5,
        "flooding": 1.5,
        "electrical": 1.5,
        "toxic": 2.0,
        "chemical": 2.0,
        "smoke": 1.0,
        "debris": 0.5,
    }

    URGENCY_SCORE = {
        "CRITICAL": 3.0,
        "HIGH": 2.0,
        "MEDIUM": 1.0,
        "LOW": 0.0,
    }

    def __init__(self):
        logger.info("Initialized RiskPriorityAgent")

    async def evaluate_risk(
        self,
        incident_data: Dict[str, Any],
        environmental_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Compute a deterministic risk and triage assessment."""

        environmental_context = environmental_context or {}

        category = str(
            incident_data.get("category", "OTHER")
        ).upper()

        urgency = str(
            incident_data.get("urgency_level", "MEDIUM")
        ).upper()

        people_count = self._non_negative_int(
            incident_data.get("people_count", incident_data.get("estimated_casualties", 0))
        )

        children_count = self._non_negative_int(
            incident_data.get("children_count", 0)
        )

        elderly_count = self._non_negative_int(
            incident_data.get("elderly_count", 0)
        )

        pregnant_count = self._non_negative_int(
            incident_data.get("pregnant_count", 0)
        )

        injured_count = self._non_negative_int(
            incident_data.get("injured_count", 0)
        )

        critical_count = self._non_negative_int(
            incident_data.get("critical_count", 0)
        )

        trapped_count = self._non_negative_int(
            incident_data.get("trapped_count", 0)
        )

        hazards = self._normalise_hazards(
            incident_data.get("hazards", [])
        )

        # ---------------------------------------------------------
        # 1. Base category severity
        # ---------------------------------------------------------

        category_score = self.CATEGORY_SEVERITY.get(category, 1.0)

        # ---------------------------------------------------------
        # 2. Explicit urgency
        # ---------------------------------------------------------

        urgency_score = self.URGENCY_SCORE.get(urgency, 1.0)

        # ---------------------------------------------------------
        # 3. Casualty and vulnerability contribution
        # ---------------------------------------------------------

        casualty_score = 0.0

        if people_count >= 20:
            casualty_score += 2.0
        elif people_count >= 10:
            casualty_score += 1.5
        elif people_count >= 5:
            casualty_score += 1.0
        elif people_count >= 1:
            casualty_score += 0.5

        casualty_score += min(injured_count * 0.5, 2.0)
        casualty_score += min(critical_count * 1.0, 3.0)
        casualty_score += min(trapped_count * 0.25, 2.0)

        vulnerable_count = (
            children_count
            + elderly_count
            + pregnant_count
        )

        vulnerability_score = min(vulnerable_count * 0.25, 1.5)

        # ---------------------------------------------------------
        # 4. Hazard contribution
        # ---------------------------------------------------------

        hazard_score = 0.0
        matched_hazards = []

        for hazard in hazards:
            for hazard_key, contribution in self.HAZARD_SEVERITY.items():
                if hazard_key in hazard:
                    hazard_score += contribution
                    matched_hazards.append(hazard)
                    break

        # Avoid allowing repeated identical hazard text to inflate
        # the score indefinitely.
        hazard_score = min(hazard_score, 3.0)

        # ---------------------------------------------------------
        # 5. Environmental context
        # ---------------------------------------------------------

        environmental_score = self._environmental_score(
            environmental_context
        )

        # ---------------------------------------------------------
        # 6. Time/casualty risk velocity
        # ---------------------------------------------------------

        elapsed_minutes = self._elapsed_minutes(
            incident_data.get("created_at")
            or incident_data.get("reported_at")
        )

        risk_velocity = self._calculate_risk_velocity(
            category=category,
            critical_count=critical_count,
            injured_count=injured_count,
            trapped_count=trapped_count,
            hazards=hazards,
            elapsed_minutes=elapsed_minutes,
        )

        # ---------------------------------------------------------
        # 7. Composite score
        # ---------------------------------------------------------

        raw_score = (
            category_score
            + urgency_score
            + casualty_score
            + vulnerability_score
            + hazard_score
            + environmental_score
            + risk_velocity["score_contribution"]
        )

        risk_score = max(1.0, min(10.0, round(raw_score, 1)))

        triage_level = self._triage_level(
            risk_score=risk_score,
            critical_count=critical_count,
            trapped_count=trapped_count,
            injured_count=injured_count,
            hazards=hazards,
        )

        # ---------------------------------------------------------
        # 8. Danger perimeter
        # ---------------------------------------------------------

        latitude = self._float_or_none(
            incident_data.get("latitude")
        )

        longitude = self._float_or_none(
            incident_data.get("longitude")
        )

        danger_radius_meters = self._danger_radius(
            risk_score=risk_score,
            category=category,
            hazards=hazards,
            environmental_context=environmental_context,
        )

        danger_polygon = []

        if latitude is not None and longitude is not None:
            danger_polygon = self._create_circle_polygon(
                latitude=latitude,
                longitude=longitude,
                radius_meters=danger_radius_meters,
            )

        rationale = self._build_rationale(
            category=category,
            urgency=urgency,
            risk_score=risk_score,
            triage_level=triage_level,
            people_count=people_count,
            injured_count=injured_count,
            critical_count=critical_count,
            trapped_count=trapped_count,
            vulnerable_count=vulnerable_count,
            hazards=hazards,
            environmental_score=environmental_score,
            risk_velocity=risk_velocity,
        )

        result = {
            "risk_score": risk_score,
            "triage_level": triage_level,
            "category": category,
            "urgency_level": urgency,

            "casualty_summary": {
                "people_count": people_count,
                "injured_count": injured_count,
                "critical_count": critical_count,
                "trapped_count": trapped_count,
                "vulnerable_count": vulnerable_count,
            },

            "hazards": hazards,
            "matched_hazards": sorted(set(matched_hazards)),

            "environmental_context": environmental_context,
            "environmental_risk_score": round(
                environmental_score,
                2,
            ),

            "elapsed_minutes": round(
                elapsed_minutes,
                2,
            ) if elapsed_minutes is not None else None,

            "casualty_risk_velocity": risk_velocity,

            "danger_radius_meters": danger_radius_meters,
            "danger_perimeter": danger_polygon,

            "score_breakdown": {
                "category_severity": category_score,
                "reported_urgency": urgency_score,
                "casualty_severity": round(casualty_score, 2),
                "vulnerability": round(vulnerability_score, 2),
                "hazards": round(hazard_score, 2),
                "environmental": round(environmental_score, 2),
                "risk_velocity": round(
                    risk_velocity["score_contribution"],
                    2,
                ),
            },

            "rationale": rationale,
        }

        logger.info(
            "Risk assessment completed: "
            f"score={risk_score}, "
            f"triage={triage_level}, "
            f"category={category}"
        )

        return result

    # =============================================================
    # Helpers
    # =============================================================

    @staticmethod
    def _non_negative_int(value: Any) -> int:
        try:
            return max(0, int(value or 0))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _float_or_none(value: Any) -> Optional[float]:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalise_hazards(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []

        return [
            str(item).strip().lower()
            for item in value
            if str(item).strip()
        ]

    @staticmethod
    def _elapsed_minutes(value: Any) -> Optional[float]:
        if value is None:
            return None

        try:
            if isinstance(value, str):
                timestamp = datetime.fromisoformat(
                    value.replace("Z", "+00:00")
                )
            elif isinstance(value, datetime):
                timestamp = value
            else:
                return None

            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(
                    tzinfo=timezone.utc
                )

            elapsed = (
                datetime.now(timezone.utc) - timestamp
            ).total_seconds() / 60.0

            return max(0.0, elapsed)

        except (TypeError, ValueError):
            return None

    @staticmethod
    def _environmental_score(
        context: Dict[str, Any],
    ) -> float:
        """Calculate environmental contribution from explicit signals."""

        score = 0.0

        boolean_weights = {
            "flood_rising": 1.5,
            "flammable_zone": 1.5,
            "gas_leak": 1.5,
            "toxic_release": 2.0,
            "structural_instability": 1.5,
            "road_blocked": 0.5,
            "bridge_collapsed": 1.5,
            "extreme_weather": 1.0,
        }

        for key, weight in boolean_weights.items():
            if context.get(key) is True:
                score += weight

        return min(score, 3.0)

    @staticmethod
    def _calculate_risk_velocity(
        category: str,
        critical_count: int,
        injured_count: int,
        trapped_count: int,
        hazards: list[str],
        elapsed_minutes: Optional[float],
    ) -> Dict[str, Any]:
        """Estimate how quickly risk is expected to worsen.

        This is a deterministic classification based only on explicit
        life-safety indicators. It is not presented as a medical
        survivability probability.
        """

        immediate = (
            critical_count > 0
            or "gas leak" in hazards
            or "explosion" in hazards
            or category == "FIRE"
        )

        high = (
            injured_count > 0
            or trapped_count > 0
            or category in {
                "BUILDING_COLLAPSE",
                "HAZARDOUS_LEAK",
                "TRAPPED_PERSONS",
                "FLOOD",
            }
        )

        if immediate:
            velocity = "VERY_HIGH"
            contribution = 1.5
        elif high:
            velocity = "HIGH"
            contribution = 1.0
        elif category == "MEDICAL_EMERGENCY":
            velocity = "MODERATE"
            contribution = 0.5
        else:
            velocity = "LOW"
            contribution = 0.0

        # Explicitly reported time can increase the assessment only
        # after meaningful elapsed intervals.
        time_factor = 0.0

        if elapsed_minutes is not None:
            if elapsed_minutes >= 60 and velocity in {
                "VERY_HIGH",
                "HIGH",
            }:
                time_factor = 0.5
            elif elapsed_minutes >= 30 and velocity == "VERY_HIGH":
                time_factor = 0.25

        return {
            "classification": velocity,
            "score_contribution": contribution + time_factor,
            "elapsed_time_factor": time_factor,
            "basis": (
                "Derived from explicit critical/injured/trapped "
                "casualties, hazard indicators, incident category, "
                "and elapsed incident time."
            ),
        }

    @staticmethod
    def _triage_level(
        risk_score: float,
        critical_count: int,
        trapped_count: int,
        injured_count: int,
        hazards: list[str],
    ) -> str:
        """Determine operational triage priority."""

        immediate_hazards = {
            "gas leak",
            "explosion",
            "toxic",
        }

        if (
            critical_count > 0
            or (
                trapped_count > 0
                and (
                    injured_count > 0
                    or any(
                        hazard in immediate_hazards
                        for hazard in hazards
                    )
                )
            )
            or risk_score >= 8.0
        ):
            return "CRITICAL"

        if (
            injured_count > 0
            or trapped_count > 0
            or risk_score >= 6.0
        ):
            return "HIGH"

        if risk_score >= 3.5:
            return "MEDIUM"

        return "LOW"

    @staticmethod
    def _danger_radius(
        risk_score: float,
        category: str,
        hazards: list[str],
        environmental_context: Dict[str, Any],
    ) -> int:
        """Calculate an operational danger radius in meters."""

        # Base radius is proportional to calculated threat.
        radius = 50 + (risk_score * 25)

        if category in {
            "FIRE",
            "HAZARDOUS_LEAK",
        }:
            radius += 50

        if any(
            hazard in {"gas leak", "explosion", "toxic", "chemical"}
            for hazard in hazards
        ):
            radius += 100

        if environmental_context.get("flammable_zone") is True:
            radius += 50

        if environmental_context.get("toxic_release") is True:
            radius += 100

        return int(round(min(radius, 1000)))

    @staticmethod
    def _create_circle_polygon(
        latitude: float,
        longitude: float,
        radius_meters: float,
        points: int = 16,
    ) -> list[Dict[str, float]]:
        """Create a geospatial polygon approximating a danger circle."""

        earth_radius = 6_378_137.0

        lat_rad = math.radians(latitude)

        polygon = []

        for index in range(points):
            angle = (
                2.0
                * math.pi
                * index
                / points
            )

            delta_lat = (
                radius_meters
                * math.cos(angle)
                / earth_radius
            )

            delta_lng = (
                radius_meters
                * math.sin(angle)
                / (
                    earth_radius
                    * max(
                        math.cos(lat_rad),
                        0.01,
                    )
                )
            )

            polygon.append(
                {
                    "latitude": round(
                        latitude
                        + math.degrees(delta_lat),
                        7,
                    ),
                    "longitude": round(
                        longitude
                        + math.degrees(delta_lng),
                        7,
                    ),
                }
            )

        return polygon

    @staticmethod
    def _build_rationale(
        category: str,
        urgency: str,
        risk_score: float,
        triage_level: str,
        people_count: int,
        injured_count: int,
        critical_count: int,
        trapped_count: int,
        vulnerable_count: int,
        hazards: list[str],
        environmental_score: float,
        risk_velocity: Dict[str, Any],
    ) -> str:
        """Create an auditable explanation for the result."""

        factors = [
            f"category={category}",
            f"reported_urgency={urgency}",
            f"people={people_count}",
            f"injured={injured_count}",
            f"critical={critical_count}",
            f"trapped={trapped_count}",
            f"vulnerable={vulnerable_count}",
            f"hazards={hazards or 'none'}",
            f"environmental_score={environmental_score}",
            f"risk_velocity={risk_velocity['classification']}",
        ]

        return (
            f"Deterministic assessment produced risk score "
            f"{risk_score}/10 and triage level {triage_level}. "
            f"Contributing factors: {', '.join(factors)}."
        )