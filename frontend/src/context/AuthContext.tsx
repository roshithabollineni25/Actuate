import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, UserRole } from '../types/auth';
import { authService } from '../services/authService';

interface AuthContextType {
  user: User | null;
  role: UserRole | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string, role?: UserRole) => Promise<void>;
  loginAsRole: (role: UserRole) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [role, setRole] = useState<UserRole | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    // Restore session from localStorage
    const savedToken = localStorage.getItem('resqmesh_token');
    const savedRole = localStorage.getItem('resqmesh_role') as UserRole | null;
    const savedUser = localStorage.getItem('resqmesh_user');

    if (savedToken && savedRole) {
      setToken(savedToken);
      setRole(savedRole);
      if (savedUser) {
        try {
          setUser(JSON.parse(savedUser));
        } catch {
          setUser({ email: `${savedRole.toLowerCase()}@resqmesh.ai`, role: savedRole });
        }
      } else {
        setUser({ email: `${savedRole.toLowerCase()}@resqmesh.ai`, role: savedRole });
      }
    }
    setIsLoading(false);
  }, []);

  const login = async (email: string, password: string, requestedRole?: UserRole) => {
    setIsLoading(true);
    try {
      const response = await authService.login(email, password, requestedRole);
      const activeRole = response.role;
      const currentUser: User = response.user || {
        email,
        role: activeRole,
        fullName: email.split('@')[0].toUpperCase(),
      };

      setToken(response.access_token);
      setRole(activeRole);
      setUser(currentUser);

      localStorage.setItem('resqmesh_token', response.access_token);
      localStorage.setItem('resqmesh_role', activeRole);
      localStorage.setItem('resqmesh_user', JSON.stringify(currentUser));
    } finally {
      setIsLoading(false);
    }
  };

  const loginAsRole = async (targetRole: UserRole) => {
    setIsLoading(true);
    try {
      const response = await authService.mockRoleLogin(targetRole);
      const currentUser: User = {
        email: `${targetRole.toLowerCase()}@resqmesh.ai`,
        role: targetRole,
        fullName: `${targetRole.replace('_', ' ')} OPERATOR`,
      };

      setToken(response.access_token);
      setRole(targetRole);
      setUser(currentUser);

      localStorage.setItem('resqmesh_token', response.access_token);
      localStorage.setItem('resqmesh_role', targetRole);
      localStorage.setItem('resqmesh_user', JSON.stringify(currentUser));
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    setToken(null);
    setRole(null);
    setUser(null);
    localStorage.removeItem('resqmesh_token');
    localStorage.removeItem('resqmesh_role');
    localStorage.removeItem('resqmesh_user');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        role,
        token,
        isAuthenticated: !!token,
        isLoading,
        login,
        loginAsRole,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
