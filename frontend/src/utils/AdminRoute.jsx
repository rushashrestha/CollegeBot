import React from 'react';
import { Navigate } from 'react-router-dom';

const AdminRoute = ({ children }) => {
  const userRole = localStorage.getItem('userRole');
  const isAuthenticated = localStorage.getItem('isAuthenticated');
  
  // Check if user is authenticated and has admin role
  if (!isAuthenticated || userRole !== 'admin') {
    return <Navigate to="/login" replace />;
  }
  
  return children;
};

export default AdminRoute;