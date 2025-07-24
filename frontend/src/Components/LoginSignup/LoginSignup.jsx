import React, { useState } from "react";
import "./Loginsignup.css";
import { useNavigate } from "react-router-dom";
import { toast, ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

const LoginSignup = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const navigate = useNavigate();

  const isValidPassword = (password) => {
    const regex = /^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{6,}$/;
    return regex.test(password);
  };

  const handleSubmit = async () => {
    if (!email || !password) {
      toast.warning("Please fill in all fields.");
      return;
    }

    if (!isLogin && password !== confirmPassword) {
      toast.error("Passwords do not match.");
      return;
    }

    if (!isLogin && !isValidPassword(password)) {
      toast.error("Password must be at least 6 characters, include a number, letter, and special character.");
      return;
    }

    // Simulate login/signup success (replace with actual authentication later)
    try {
      if (isLogin) {
        // Simulate login
        toast.success("Login successful!");
        setTimeout(() => navigate("/chat"), 1500);
      } else {
        // Simulate signup
        toast.success("Account created successfully!");
        setTimeout(() => navigate("/chat"), 1500);
      }
    } catch (error) {
      toast.error("Something went wrong. Please try again.");
    }
  };

  return (
    <div className="login-signup-container">
      <ToastContainer position="top-right" toastStyle={{ marginTop: "70px" }} />
      <div className="form-section">
        <h2>{isLogin ? "Login to Samriddhi ChatBot" : "Join Samriddhi ChatBot"}</h2>
        <input
          type="email"
          placeholder="Email Address"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {!isLogin && (
          <input
            type="password"
            placeholder="Confirm Password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
          />
        )}
        <button onClick={handleSubmit}>
          {isLogin ? "Continue" : "Register"}
        </button>
        <p>
          {isLogin ? "Don't have an account?" : "Already have an account?"}
          <span onClick={() => setIsLogin(!isLogin)}>
            {isLogin ? " Sign Up" : " Login"}
          </span>
        </p>
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
  );
};

export default LoginSignup;