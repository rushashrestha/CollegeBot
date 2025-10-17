import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LoginSignup from './Components/LoginSignup/LoginSignup';
import ChatBot from './Components/ChatBot/ChatBot';
import AdminDashboard from './Components/AdminDashboard/AdminDashboard';
import AdminRoute from './utils/AdminRoute';
import ProtectedRoute from './utils/ProtectedRoute';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          {/* Default route - redirect to login */}
          <Route path="/" element={<Navigate to="/login" replace />} />
          
          {/* Login/Signup route - redirect to chat if already authenticated */}
          <Route 
            path="/login" 
            element={
              <ProtectedRoute requireAuth={false}>
                <LoginSignup />
              </ProtectedRoute>
            } 
          />
          
          {/* Chat route - protected, only for authenticated users */}
          <Route 
            path="/chat" 
            element={
              <ProtectedRoute>
                <ChatBot />
              </ProtectedRoute>
            } 
          />
          
          {/* Admin route - protected, only for admin users */}
          <Route 
            path="/admin" 
            element={
              <AdminRoute>
                <AdminDashboard />
              </AdminRoute>
            } 
          />
          
          {/* Catch all route - redirect to login */}
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;