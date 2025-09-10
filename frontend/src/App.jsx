import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LoginSignup from './Components/LoginSignup/LoginSignup';
import ChatBot from './Components/ChatBot/ChatBot';
import AdminDashboard from './Components/AdminDashboard/AdminDashboard';
import AdminRoute from './utils/AdminRoute';
import ChangePassword from "./Components/ChangePassword/ChangePassword";

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          {/* Default route - redirect to login */}
          <Route path="/" element={<Navigate to="/login" replace />} />
          
          {/* Login/Signup route */}
          <Route path="/login" element={<LoginSignup />} />
          
          {/* Chat route - accessible to all authenticated users and guests */}
          <Route path="/chat" element={<ChatBot />} />

          <Route path="/change-password" element={<ChangePassword />} />
          
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