export type IncidentCategory =
  | 'FLOOD'
  | 'FIRE'
  | 'BUILDING_COLLAPSE'
  | 'MEDICAL_EMERGENCY'
  | 'TRAPPED_PERSONS'
  | 'HAZARDOUS_LEAK'
  | 'OTHER';

export type UrgencyLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type IncidentStatus =
  | 'REPORTED'
  | 'TRIAGED'
  | 'MISSION_PROPOSED'
  | 'IN_PROGRESS'
  | 'RESOLVED'
  | 'CANCELLED';

export interface Incident {
  id: number;
  title: string;
  category: IncidentCategory;
  urgencyLevel: UrgencyLevel;
  status: IncidentStatus;
  latitude: number;
  longitude: number;
  address?: string;
  description?: string;
  estimatedCasualties: number;
  createdAt: string;
}
