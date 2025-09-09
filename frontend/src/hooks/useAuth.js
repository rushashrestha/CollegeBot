// src/hooks/useAuth.js
import { useState, useEffect } from 'react';
import authService from '../services/authService';

export function useAuth() {
  const [authState, setAuthState] = useState({
    user: null,
    userRole: null,
    userDetails: null,
    isLoading: true,
    isAuthenticated: false,
    isTeacher: false,
    isStudent: false,
    requiresPasswordChange: false
  });

  useEffect(() => {
    // Subscribe to auth state changes
    const unsubscribe = authService.onAuthStateChanged((newState) => {
      setAuthState({
        user: newState.user,
        userRole: newState.userRole,
        userDetails: newState.userDetails,
        isLoading: newState.isLoading,
        isAuthenticated: !!newState.user,
        isTeacher: newState.userRole === 'teacher',
        isStudent: newState.userRole === 'student',
        requiresPasswordChange: newState.userDetails?.mustChangePassword || false
      });
    });

    // Set initial state
    const currentState = authService.getAuthState();
    setAuthState(currentState);

    // Cleanup subscription
    return () => unsubscribe();
  }, []);

  // Auth methods
  const login = async (email, password) => {
    return await authService.login(email, password);
  };

  const logout = async () => {
    return await authService.logout();
  };

  const changePassword = async (newPassword, confirmPassword) => {
    return await authService.changePassword(newPassword, confirmPassword);
  };

  const resetPassword = async (email) => {
    return await authService.resetPassword(email);
  };

  const queryStudentData = async (searchTerm, filters) => {
    return await authService.queryStudentData(searchTerm, filters);
  };

  const getMyData = async () => {
    return await authService.getMyData();
  };

  return {
    // State
    ...authState,
    
    // Methods
    login,
    logout,
    changePassword,
    resetPassword,
    queryStudentData,
    getMyData
  };
}