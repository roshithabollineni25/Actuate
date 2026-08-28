export type UserRole = 'CITIZEN' | 'ADMIN' | 'RESCUE_TEAM';

export interface User {
  id?: number | string;
  email: string;
  fullName?: string;
  role: UserRole;
  phoneNumber?: string;
  isActive?: boolean;
}

export interface AuthState {
  user: User | null;
  role: UserRole | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: UserRole;
  user?: User;
}
