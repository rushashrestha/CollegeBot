import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast, ToastContainer } from "react-toastify";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { loginUser } from "../../utils/auth";
import "react-toastify/dist/ReactToastify.css";
import "./LoginSignup.css";

// ✅ Schema for validation
const loginSchema = z.object({
  email: z.string().email("Invalid email address"),
  password: z.string().min(6, "Password must be at least 6 characters"),
});

const Login = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data) => {
    const { email, password } = data;
    setIsLoading(true);

    try {
      // Check for admin login first (preserve original admin functionality)
      if (email === "admin@samriddhi.edu.np" && password === "admin123") {
        toast.success("Admin login successful!");
        localStorage.setItem("userRole", "admin");
        localStorage.setItem("adminEmail", email);
        localStorage.setItem("isAuthenticated", "true");
        setTimeout(() => navigate("/admin"), 1500);
        return;
      } // Regular user login with Supabase

      const { data: authData, error } = await loginUser(email, password);

      if (error) {
        // ✅ UPDATED LINE: Log the error and ensure a string message is displayed
        console.error("Supabase Login Failed:", error); // Use the returned error message, with a robust fallback
        toast.error(
          String(error) || "Login failed. Invalid email or password."
        );
        return;
      }

      if (authData?.user) {
        toast.success("Login successful!"); // Store user info in localStorage for compatibility with existing components

        localStorage.setItem("userRole", "user");
        localStorage.setItem("userEmail", email);
        localStorage.setItem("isAuthenticated", "true");
        localStorage.setItem("supabase_user_id", authData.user.id);

        setTimeout(() => navigate("/chat"), 1500);
      } else {
        // Fallback for an odd case where no user or error is returned (shouldn't happen)
        toast.error("Login attempt failed. Please re-check credentials.");
      }
    } catch (error) {
      console.error("Login component catch block error:", error);
      toast.error("Something went wrong. Please check your connection.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-container">
            <ToastContainer toastStyle={{ marginTop: "70px" }} />     {" "}
      <div className="form-section">
                <h2>Login to AskSamriddhi</h2>       {" "}
        <form onSubmit={handleSubmit(onSubmit)} className="login-form">
                   {" "}
          <div className="input-group">
                       {" "}
            <input
              type="email"
              placeholder="Email Address"
              {...register("email")}
              className="login-input"
              disabled={isLoading}
            />
                       {" "}
            {errors.email && (
              <p className="error-text">{errors.email.message}</p>
            )}
                     {" "}
          </div>
                   {" "}
          <div className="input-group">
                       {" "}
            <input
              type="password"
              placeholder="Password"
              {...register("password")}
              className="login-input"
              disabled={isLoading}
            />
                       {" "}
            {errors.password && (
              <p className="error-text">{errors.password.message}</p>
            )}
                     {" "}
          </div>
                   {" "}
          <button type="submit" className="login-btn" disabled={isLoading}>
                        {isLoading ? "Logging in..." : "Continue"}         {" "}
          </button>
                 {" "}
        </form>
               {" "}
        <div className="access-options">
                   {" "}
          <div className="guest-access">
                        <p>or</p>           {" "}
            <button
              className="guest-btn"
              onClick={() => {
                // Mark as guest for ProtectedRoute
                localStorage.setItem("userRole", "guest");
                localStorage.setItem("isAuthenticated", "true");
                navigate("/chat");
              }}
              disabled={isLoading}
            >
                            Continue as Guest            {" "}
            </button>
                     {" "}
          </div>
                 {" "}
        </div>
             {" "}
      </div>
         {" "}
    </div>
  );
};

export default Login;
