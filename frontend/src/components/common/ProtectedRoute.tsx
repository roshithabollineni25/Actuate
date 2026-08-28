import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { UserRole } from '../../types/auth';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: UserRole[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles }) => {
  const { isAuthenticated, role, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-tactical-900 text-slate-400">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          <span className="font-mono text-xs uppercase tracking-wider">Authenticating Mesh Session...</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && role && !allowedRoles.includes(role)) {
    // If role doesn't match, route to corresponding appropriate dashboard
    if (role === 'CITIZEN') return <Navigate to="/citizen" replace />;
    if (role === 'ADMIN') return <Navigate to="/admin" replace />;
    if (role === 'RESCUE_TEAM') return <Navigate to="/rescue" replace />;
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
};
