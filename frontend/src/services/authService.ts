import { apiClient } from './apiClient';
import { UserRole, LoginResponse } from '../types/auth';

export const authService = {
  async login(email: string, password: string, requestedRole?: UserRole): Promise<LoginResponse> {
    const response = await apiClient.post<LoginResponse>('/auth/login', {
      email,
      password,
      requested_role: requestedRole,
    });
    return response.data;
  },

  async mockRoleLogin(role: UserRole): Promise<LoginResponse> {
    const email = `${role.toLowerCase()}@resqmesh.ai`;
    const response = await apiClient.post<LoginResponse>('/auth/login', {
      email,
      password: 'demo-password-123',
      requested_role: role,
    });
    return response.data;
  },
};
