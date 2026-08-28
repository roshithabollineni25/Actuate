import { apiClient } from './apiClient';

export interface SituationAnalysisRequest {
  raw_text?: string;
  audio_url?: string;
  metadata?: Record<string, unknown>;
}

export interface SituationAnalysisResponse {
  category: string;
  urgency_level: string;
  people_count: number;
  children_count: number;
  elderly_count: number;
  pregnant_count: number;
  injured_count: number;
  critical_count: number;
  trapped_count: number;
  medical_needs: string[];
  hazards: string[];
  location_description?: string | null;
  summary: string;
}

export interface IncidentCreateRequest {
  title?: string | null;
  description?: string | null;
  category: string;
  urgency_level: string;
  latitude: number;
  longitude: number;
  address?: string | null;
  raw_input_text?: string | null;
  audio_file_url?: string | null;
  estimated_casualties?: number;
}

export interface IncidentResponse {
  id: number;
  reporter_id?: number | null;

  title?: string | null;
  description?: string | null;

  category: string;
  urgency_level: string;
  status: string;
  active_mission_status?: string | null;

  latitude: number;
  longitude: number;

  address?: string | null;

  raw_input_text?: string | null;
  audio_file_url?: string | null;

  estimated_casualties: number;

  created_at: string;
  updated_at: string;
}

export const incidentService = {
  async analyzeSituation(
    request: SituationAnalysisRequest,
  ): Promise<SituationAnalysisResponse> {
    const response = await apiClient.post<SituationAnalysisResponse>(
      '/incidents/analyze',
      request,
    );

    return response.data;
  },

  async createIncident(
    request: IncidentCreateRequest,
  ): Promise<IncidentResponse> {
    const response = await apiClient.post<IncidentResponse>(
      '/incidents',
      request,
    );

    return response.data;
  },

  async getIncidents(): Promise<IncidentResponse[]> {
    const response = await apiClient.get<IncidentResponse[]>('/incidents');

    return response.data;
  },

  async getIncident(incidentId: number): Promise<IncidentResponse> {
    const response = await apiClient.get<IncidentResponse>(
      `/incidents/${incidentId}`,
    );

    return response.data;
  },
};