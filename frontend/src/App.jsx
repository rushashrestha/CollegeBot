import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LoginSignup from './Components/LoginSignup/LoginSignup';
import ChatBot from './Components/ChatBot/ChatBot';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          {/* Default route redirects to login */}
          <Route path="/" element={<Navigate to="/login" replace />} />
          
          {/* Login/Signup page */}
          <Route path="/login" element={<LoginSignup />} />
          
          {/* Chat page */}
          <Route path="/chat" element={<ChatBot />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;