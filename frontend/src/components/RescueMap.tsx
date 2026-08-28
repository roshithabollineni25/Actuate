import React from "react";
import {
  MapContainer,
  Marker,
  Polyline,
  Popup,
  TileLayer,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

type Coordinate = [number, number];

export interface RoadHazardProp {
  id: number;
  road_name?: string;
  condition?: string;
  latitude_start: number;
  longitude_start: number;
  latitude_end?: number | null;
  longitude_end?: number | null;
  hazard_notes?: string;
}

interface RescueMapProps {
  route: Coordinate[];
  detourRoute?: Coordinate[];
  incident?: Coordinate;
  teamLocation?: Coordinate;
  hazards?: RoadHazardProp[];
}

const incidentIcon = new L.Icon({
  iconUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
});

function FitBounds({ points }: { points: Coordinate[] }) {
  const map = useMap();

  if (points.length > 1) {
    map.fitBounds(points, {
      padding: [40, 40],
    });
  }

  return null;
}

export default function RescueMap({
  route,
  detourRoute,
  incident,
  teamLocation,
  hazards = [],
}: RescueMapProps) {
  const fallbackCenter: Coordinate = [17.4400, 78.3800];

  const allPoints: Coordinate[] = [
    ...route,
    ...(detourRoute || []),
    ...(incident ? [incident] : []),
    ...(teamLocation ? [teamLocation] : []),
  ];

  const center: Coordinate =
    allPoints.length > 0
      ? allPoints[0]
      : fallbackCenter;

  return (
    <div
      style={{
        width: "100%",
        height: "430px",
        borderRadius: "12px",
        overflow: "hidden",
        border: "1px solid rgba(59, 130, 246, 0.25)",
      }}
    >
      <MapContainer
        center={center}
        zoom={14}
        scrollWheelZoom={true}
        style={{
          width: "100%",
          height: "100%",
        }}
      >
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <FitBounds points={allPoints} />

        {/* Primary Route */}
        {route.length > 1 && (
          <Polyline
            positions={route}
            pathOptions={{
              color: "#3b82f6",
              weight: 6,
              opacity: 0.9,
            }}
          />
        )}

        {/* Detour Route */}
        {detourRoute && detourRoute.length > 1 && (
          <Polyline
            positions={detourRoute}
            pathOptions={{
              color: "#a855f7",
              weight: 6,
              dashArray: "10, 10",
              opacity: 0.9,
            }}
          />
        )}

        {/* Road Hazards */}
        {hazards.map((hazard) => {
          const hasSegment =
            hazard.latitude_end != null && hazard.longitude_end != null;

          return (
            <React.Fragment key={hazard.id}>
              {hasSegment ? (
                <Polyline
                  positions={[
                    [hazard.latitude_start, hazard.longitude_start],
                    [hazard.latitude_end!, hazard.longitude_end!],
                  ]}
                  pathOptions={{
                    color: "#ef4444",
                    weight: 8,
                    opacity: 0.85,
                  }}
                >
                  <Popup>
                    <strong style={{ color: "#ef4444" }}>
                      ROAD HAZARD: {hazard.condition || "BLOCKED"}
                    </strong>
                    <br />
                    {hazard.road_name || "Blocked Segment"}
                    {hazard.hazard_notes && <br />}
                    {hazard.hazard_notes}
                  </Popup>
                </Polyline>
              ) : (
                <Marker
                  position={[hazard.latitude_start, hazard.longitude_start]}
                >
                  <Popup>
                    <strong style={{ color: "#ef4444" }}>
                      ROAD HAZARD: {hazard.condition || "BLOCKED"}
                    </strong>
                    <br />
                    {hazard.road_name || "Hazard Location"}
                  </Popup>
                </Marker>
              )}
            </React.Fragment>
          );
        })}

        {/* Incident Location */}
        {incident && (
          <Marker position={incident} icon={incidentIcon}>
            <Popup>
              <strong>Emergency Incident</strong>
              <br />
              Target Location
            </Popup>
          </Marker>
        )}

        {/* Team Location */}
        {teamLocation && (
          <Marker position={teamLocation}>
            <Popup>
              <strong>Rescue Team</strong>
              <br />
              Current Position
            </Popup>
          </Marker>
        )}
      </MapContainer>
    </div>
  );
}