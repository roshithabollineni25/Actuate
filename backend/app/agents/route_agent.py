"""Deterministic Route Intelligence Agent."""

import math
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.road_status import RoadStatus, RoadCondition


class RouteIntelligenceAgent:
    """
    Deterministic safe-route calculation.

    Routing:
    - OSRM road-network routing
    - RoadStatus hazard filtering
    - Haversine geometry checks
    """

    OSRM_BASE_URL = "https://router.project-osrm.org"

    # Hazard buffer around reported road segments (250m).
    HAZARD_BUFFER_KM = 0.25
    ROUTE_START_IGNORE_KM = 0.15

    BLOCKING_CONDITIONS = {
        RoadCondition.FLOODED,
        RoadCondition.BLOCKED,
        RoadCondition.DEBRIS_RESTRICTED,
        RoadCondition.BRIDGE_COLLAPSED,
        RoadCondition.HAZARDOUS,
    }

    def __init__(self):
        logger.info("Initialized RouteIntelligenceAgent")

    @staticmethod
    def _haversine_km(
        lat1: float,
        lng1: float,
        lat2: float,
        lng2: float,
    ) -> float:
        """Calculate great-circle distance."""

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

    @classmethod
    def _point_to_segment_distance_km(
        cls,
        point_lat: float,
        point_lng: float,
        start_lat: float,
        start_lng: float,
        end_lat: float,
        end_lng: float,
    ) -> float:
        """
        Approximate point-to-segment distance.

        Suitable for short road segments where a local
        equirectangular projection is sufficiently accurate.
        """

        mean_lat = math.radians(
            (point_lat + start_lat + end_lat) / 3
        )

        scale_lat = 111.32
        scale_lng = 111.32 * math.cos(mean_lat)

        px = point_lng * scale_lng
        py = point_lat * scale_lat

        ax = start_lng * scale_lng
        ay = start_lat * scale_lat

        bx = end_lng * scale_lng
        by = end_lat * scale_lat

        dx = bx - ax
        dy = by - ay

        if dx == 0 and dy == 0:
            return cls._haversine_km(
                point_lat,
                point_lng,
                start_lat,
                start_lng,
            )

        t = (
            (px - ax) * dx
            + (py - ay) * dy
        ) / (dx * dx + dy * dy)

        t = max(0.0, min(1.0, t))

        closest_x = ax + t * dx
        closest_y = ay + t * dy

        distance_km = math.sqrt(
            (px - closest_x) ** 2
            + (py - closest_y) ** 2
        )

        return distance_km

    @classmethod
    def _route_intersects_hazard(
        cls,
        route_coordinates: List[List[float]],
        hazard: RoadStatus,
    ) -> bool:
        """
        Determine whether the route passes through a hazardous road segment.
        """

        if not route_coordinates:
            return False

        if (
            hazard.latitude_end is None
            or hazard.longitude_end is None
        ):
            for lng, lat in route_coordinates:
                if (
                    cls._haversine_km(
                        lat,
                        lng,
                        hazard.latitude_start,
                        hazard.longitude_start,
                    )
                    <= cls.HAZARD_BUFFER_KM
                ):
                    return True

            return False

        for lng, lat in route_coordinates:
            distance = cls._point_to_segment_distance_km(
                lat,
                lng,
                hazard.latitude_start,
                hazard.longitude_start,
                hazard.latitude_end,
                hazard.longitude_end,
            )

            if distance <= cls.HAZARD_BUFFER_KM:
                return True

        return False

    async def _request_osrm_routes(
        self,
        origin_lat: float,
        origin_lng: float,
        destination_lat: float,
        destination_lng: float,
    ) -> List[Dict[str, Any]]:
        """Request actual road-network routes from OSRM."""

        coordinates = (
            f"{origin_lng},{origin_lat};"
            f"{destination_lng},{destination_lat}"
        )

        url = (
            f"{self.OSRM_BASE_URL}/route/v1/driving/"
            f"{coordinates}"
        )

        params = {
            "alternatives": "true",
            "steps": "true",
            "overview": "full",
            "geometries": "geojson",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                url,
                params=params,
            )

        response.raise_for_status()

        payload = response.json()

        if payload.get("code") != "Ok":
            raise RuntimeError(
                f"OSRM routing failed: {payload.get('code')}"
            )

        routes = payload.get("routes", [])

        if not routes:
            raise RuntimeError(
                "OSRM returned no route."
            )

        return routes

    async def compute_safe_route(
        self,
        origin_lat: float,
        origin_lng: float,
        destination_lat: float,
        destination_lng: float,
        db: Session,
        avoid_hazards: bool = True,
        active_road_status_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Calculate deterministic route geometry and ETA.

        Routes come from the real road network via OSRM.
        Hazard filtering uses RoadStatus records from the database.
        Never uses fake straight-line fallback.
        """

        if not (
            -90 <= origin_lat <= 90
            and -180 <= origin_lng <= 180
            and -90 <= destination_lat <= 90
            and -180 <= destination_lng <= 180
        ):
            raise ValueError("Invalid geographic coordinates.")

        hazards: List[RoadStatus] = []

        if avoid_hazards:
            hazard_query = db.query(RoadStatus).filter(
                RoadStatus.condition.in_(
                    list(self.BLOCKING_CONDITIONS)
                )
            )

            if active_road_status_ids:
                hazard_query = hazard_query.filter(
                    RoadStatus.id.in_(active_road_status_ids)
                )

            hazards = hazard_query.all()

        try:
            routes = await self._request_osrm_routes(
                origin_lat,
                origin_lng,
                destination_lat,
                destination_lng,
            )
        except Exception as exc:
            logger.error(f"OSRM route calculation failed: {exc}")
            raise RuntimeError(f"OSRM routing service unavailable: {exc}")

        evaluated_routes = []

        for index, route in enumerate(routes):
            geometry = route.get("geometry", {}).get("coordinates", [])
            blocked_hazards = []

            for hazard in hazards:
                if self._route_intersects_hazard(geometry, hazard):
                    blocked_hazards.append({
                        "road_status_id": hazard.id,
                        "road_name": hazard.road_name,
                        "condition": hazard.condition.value,
                        "hazard_notes": hazard.hazard_notes,
                    })

            dist_km = round(route.get("distance", 0) / 1000, 2)
            duration_mins = round(route.get("duration", 0) / 60, 1)

            if duration_mins < 1.0 and dist_km > 0.5:
                duration_mins = round((dist_km / 0.667) + 2.0, 1)

            evaluated_routes.append({
                "route_index": index,
                "distance_km": dist_km,
                "duration_minutes": duration_mins,
                "geometry": geometry,
                "steps": route.get("legs", []),
                "blocked": bool(blocked_hazards),
                "blocked_hazards": blocked_hazards,
            })

        safe_routes = [r for r in evaluated_routes if not r["blocked"]]

        if not safe_routes:
            logger.warning(
                "All direct OSRM routes blocked. Searching for detour."
            )

            # Generate candidate detour waypoints around blocked hazards
            detour_waypoints = []

            for hazard in hazards:
                if (
                    hazard.latitude_start is None
                    or hazard.longitude_start is None
                ):
                    continue

                if (
                    hazard.latitude_end is not None
                    and hazard.longitude_end is not None
                ):
                    hazard_lat = (hazard.latitude_start + hazard.latitude_end) / 2
                    hazard_lng = (hazard.longitude_start + hazard.longitude_end) / 2
                else:
                    hazard_lat = hazard.latitude_start
                    hazard_lng = hazard.longitude_start

                for offset in [0.005, 0.010, 0.018, 0.028, 0.040]:
                    detour_waypoints.extend([
                        [hazard_lng + offset, hazard_lat],
                        [hazard_lng - offset, hazard_lat],
                        [hazard_lng, hazard_lat + offset],
                        [hazard_lng, hazard_lat - offset],
                        [hazard_lng + offset, hazard_lat + offset],
                        [hazard_lng - offset, hazard_lat - offset],
                        [hazard_lng + offset, hazard_lat - offset],
                        [hazard_lng - offset, hazard_lat + offset],
                    ])

            detour_attempts = 0

            for waypoint in detour_waypoints:
                detour_attempts += 1
                try:
                    coordinates = (
                        f"{origin_lng},{origin_lat};"
                        f"{waypoint[0]},{waypoint[1]};"
                        f"{destination_lng},{destination_lat}"
                    )

                    url = (
                        f"{self.OSRM_BASE_URL}/route/v1/driving/"
                        f"{coordinates}"
                    )

                    params = {
                        "alternatives": "false",
                        "steps": "true",
                        "overview": "full",
                        "geometries": "geojson",
                    }

                    async with httpx.AsyncClient(timeout=10.0) as client:
                        response = await client.get(
                            url,
                            params=params,
                        )

                    response.raise_for_status()
                    payload = response.json()

                    if payload.get("code") != "Ok":
                        continue

                    candidate_routes = payload.get("routes", [])

                    if not candidate_routes:
                        continue

                    candidate = candidate_routes[0]

                    geometry = (
                        candidate
                        .get("geometry", {})
                        .get("coordinates", [])
                    )

                    blocked_hazards = []

                    for hazard in hazards:
                        if self._route_intersects_hazard(
                            geometry,
                            hazard,
                        ):
                            blocked_hazards.append({
                                "road_status_id": hazard.id,
                                "road_name": hazard.road_name,
                                "condition": hazard.condition.value,
                                "hazard_notes": hazard.hazard_notes,
                            })

                    if blocked_hazards:
                        continue

                    dist_km = round(
                        candidate.get("distance", 0) / 1000,
                        2,
                    )

                    duration_mins = round(
                        candidate.get("duration", 0) / 60,
                        1,
                    )

                    detour_route = {
                        "route_index": 1000 + len(evaluated_routes),
                        "distance_km": dist_km,
                        "duration_minutes": duration_mins,
                        "geometry": geometry,
                        "steps": candidate.get("legs", []),
                        "blocked": False,
                        "blocked_hazards": [],
                    }

                    safe_routes.append(detour_route)
                    evaluated_routes.append(detour_route)

                    logger.info(
                        "Safe detour found via OSRM: %.2f km, %.1f minutes",
                        dist_km,
                        duration_mins,
                    )

                    break

                except Exception as exc:
                    logger.debug("Detour route attempt failed: %s", exc)

                if safe_routes:
                    break

            if not safe_routes:
                logger.warning(
                    "No safe detour found after %d OSRM waypoint attempts.",
                    detour_attempts,
                )
                return {
                    "route_status": "NO_SAFE_ROUTE",
                    "safety_status": "HAZARD_BLOCKED",
                    "origin": {
                        "latitude": origin_lat,
                        "longitude": origin_lng,
                    },
                    "destination": {
                        "latitude": destination_lat,
                        "longitude": destination_lng,
                    },
                    "hazards_considered": len(hazards),
                    "routes_evaluated": evaluated_routes,
                    "detour_attempts": detour_attempts,
                    "route_summary": (
                        "No safe road-network route could be found "
                        "after evaluating direct routes and detours."
                    ),
                    "message": (
                        "Active road hazards blocked the available "
                        "routes and no safe detour was found."
                    ),
                }

        safe_routes.sort(key=lambda r: (r["duration_minutes"], r["distance_km"]))
        selected = safe_routes[0]

        logger.info(f"Safe route calculated: {selected['distance_km']} km, {selected['duration_minutes']} minutes")

        return {
            "route_status": "SAFE_ROUTE_FOUND",
            "safety_status": "CLEAR",
            "origin": {"latitude": origin_lat, "longitude": origin_lng},
            "destination": {"latitude": destination_lat, "longitude": destination_lng},
            "distance_km": selected["distance_km"],
            "distance": f"{selected['distance_km']} km",
            "eta_minutes": selected["duration_minutes"],
            "ETA": f"{selected['duration_minutes']} mins",
            "route_polyline": [
    [coord[1], coord[0]]
    for coord in selected["geometry"]
],
"route": [
    [coord[1], coord[0]]
    for coord in selected["geometry"]
],
            "turn_by_turn": selected["steps"],
            "hazards_considered": len(hazards),
            "hazard_avoidance_enabled": avoid_hazards,
            "alternative_routes_evaluated": len(evaluated_routes),
            "detour_attempts": len(evaluated_routes) - len(routes),
            "rejected_routes": [r for r in evaluated_routes if r["blocked"]],
            "routing_engine": "OSRM",
            "route_summary": f"Optimal road network route via OSRM ({selected['distance_km']} km, {selected['duration_minutes']} mins).",
            "is_simulated": False,
        }