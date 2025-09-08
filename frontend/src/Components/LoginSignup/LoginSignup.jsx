// Login.jsx
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast, ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import "./LoginSignup.css";

const Login = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const navigate = useNavigate();

  const handleSubmit = async () => {
    if (!email || !password) {
      toast.warning("Please fill in all fields.");
      return;
    }

    try {
      // Check for admin credentials
      if (email === 'admin@samriddhi.edu.np' && password === 'admin123') {
        toast.success("Admin login successful!");
        localStorage.setItem('userRole', 'admin');
        localStorage.setItem('adminEmail', email);
        localStorage.setItem('isAuthenticated', 'true');
        setTimeout(() => navigate("/admin"), 1500);
      } else {
        // Regular user login
        toast.success("Login successful!");
        localStorage.setItem('userRole', 'user');
        localStorage.setItem('userEmail', email);
        localStorage.setItem('isAuthenticated', 'true');
        setTimeout(() => navigate("/chat"), 1500);
      }
    } catch (error) {
      toast.error("Something went wrong. Please try again.");
    }
  };

  return (
    <div className="login-container">
      <ToastContainer position="top-right" toastStyle={{ marginTop: "70px" }} />
      <div className="form-section">
        <h2>Login to AskSamriddhi</h2>
        
        <input
          type="email"
          placeholder="Email Address"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="login-input"
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="login-input"
        />
        
        <button onClick={handleSubmit}>
          Continue
        </button>

        <div className="access-options">
          <div className="guest-access">
            <p>or</p>
            <button 
              className="guest-btn"
              onClick={() => navigate("/chat")}
            >
              Continue as Guest
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;