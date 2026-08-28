import { apiClient } from './apiClient';

export interface HealthCheckResponse {
  status: string;
  service: string;
}

export const healthService = {
  async getHealth(): Promise<HealthCheckResponse> {
    const response = await apiClient.get<HealthCheckResponse>('/health');
    return response.data;
  },
};
