import React from "react";
import { useNavigate } from "react-router-dom";
import { toast, ToastContainer } from "react-toastify";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import "react-toastify/dist/ReactToastify.css";
import "./LoginSignup.css";

// ✅ Schema for validation
const loginSchema = z.object({
  email: z.email("Invalid email address"),
  password: z.string().min(6, "Password must be at least 6 characters"),
});

const Login = () => {
  const navigate = useNavigate();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = (data) => {
    const { email, password } = data;

    try {
      if (email === "admin@samriddhi.edu.np" && password === "admin123") {
        toast.success("Admin login successful!");
        localStorage.setItem("userRole", "admin");
        localStorage.setItem("adminEmail", email);
        localStorage.setItem("isAuthenticated", "true");
        setTimeout(() => navigate("/admin"), 1500);
      } else {
        toast.success("Login successful!");
        localStorage.setItem("userRole", "user");
        localStorage.setItem("userEmail", email);
        localStorage.setItem("isAuthenticated", "true");
        setTimeout(() => navigate("/chat"), 1500);
      }
    } catch (error) {
      toast.error("Something went wrong. Please try again.");
    }
  };

  return (
    <div className="login-container">
      <ToastContainer  toastStyle={{ marginTop: "70px" }} />
      <div className="form-section">
        <h2>Login to AskSamriddhi</h2>

        <form onSubmit={handleSubmit(onSubmit)} className="login-form">
          <div className="input-group">
            <input
              type="email"
              placeholder="Email Address"
              {...register("email")}
              className="login-input"
            />
            {errors.email && (
              <p className="error-text">{errors.email.message}</p>
            )}
          </div>

          <div className="input-group">
            <input
              type="password"
              placeholder="Password"
              {...register("password")}
              className="login-input"
            />
            {errors.password && (
              <p className="error-text">{errors.password.message}</p>
            )}
          </div>

          <button type="submit" className="login-btn">Continue</button>
        </form>

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
