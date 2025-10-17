import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast, ToastContainer } from "react-toastify";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { loginUser, getUserRole } from "../../utils/auth"; // ✅ Import getUserRole
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
      // ✅ Clear any old auth buffer first
      sessionStorage.removeItem("authBuffer");
      
      // Check for admin login first (preserve original admin functionality)
      if (email === "admin@samriddhi.edu.np" && password === "admin123") {
        // ✅ Set BOTH localStorage AND sessionStorage
        const authData = {
          userRole: "admin",
          userEmail: email,
          isAuthenticated: "true",
          timestamp: Date.now()
        };
        
        localStorage.setItem("userRole", "admin");
        localStorage.setItem("adminEmail", email);
        localStorage.setItem("isAuthenticated", "true");
        
        // Session storage as immediate buffer
        sessionStorage.setItem("authBuffer", JSON.stringify(authData));
        
        console.log("✅ Admin auth set, navigating...");
        toast.success("Admin login successful!");
        
        // Navigate immediately
        navigate("/admin", { replace: true });
        setIsLoading(false);
        return;
      }

      // Regular user login with Supabase
      console.log("🔐 Attempting Supabase login for:", email);
      const { data: authData, error } = await loginUser(email, password);

      if (error) {
        console.error("❌ Supabase Login Failed:", error);
        // Clear any partial auth data
        sessionStorage.removeItem("authBuffer");
        toast.error(
          String(error) || "Login failed. Invalid email or password."
        );
        setIsLoading(false);
        return;
      }

      if (authData?.user) {
        console.log("✅ Supabase login successful, fetching role...");
        
        // ✅ FIX: Get the actual user role from database
        const userRole = await getUserRole(email);
        console.log("✅ User role detected:", userRole);

        // ✅ Check if role was found
        if (!userRole || userRole === 'guest') {
          console.error("❌ No valid role found for user");
          toast.error("Account not found in system. Please contact admin.");
          sessionStorage.removeItem("authBuffer");
          setIsLoading(false);
          return;
        }

        // ✅ Set BOTH localStorage AND sessionStorage immediately
        const authBufferData = {
          userRole: userRole,
          userEmail: email,
          isAuthenticated: "true",
          userId: authData.user.id,
          timestamp: Date.now()
        };
        
        localStorage.setItem("userRole", userRole);
        localStorage.setItem("userEmail", email);
        localStorage.setItem("isAuthenticated", "true");
        localStorage.setItem("supabase_user_id", authData.user.id);
        
        // Session storage as immediate buffer
        sessionStorage.setItem("authBuffer", JSON.stringify(authBufferData));

        console.log("✅ Auth data set:", authBufferData);
        toast.success(`Login successful as ${userRole}!`);

        // Navigate immediately
        navigate("/chat", { replace: true });
        setIsLoading(false);
      } else {
        toast.error("Login attempt failed. Please re-check credentials.");
        sessionStorage.removeItem("authBuffer");
        setIsLoading(false);
      }
    } catch (error) {
      console.error("💥 Login component catch block error:", error);
      toast.error("Something went wrong. Please check your connection.");
      sessionStorage.removeItem("authBuffer");
      setIsLoading(false);
    }
  };

  return (
    <div className="login-container">
      <ToastContainer toastStyle={{ marginTop: "70px" }} />
      <div className="form-section">
        <h2>Login to AskSamriddhi</h2>
        <form onSubmit={handleSubmit(onSubmit)} className="login-form">
          <div className="input-group">
            <input
              type="email"
              placeholder="Email Address"
              {...register("email")}
              className="login-input"
              disabled={isLoading}
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
              disabled={isLoading}
            />
            {errors.password && (
              <p className="error-text">{errors.password.message}</p>
            )}
          </div>
          <button type="submit" className="login-btn" disabled={isLoading}>
            {isLoading ? "Logging in..." : "Continue"}
          </button>
        </form>
        <div className="access-options">
          <div className="guest-access">
            <p>or</p>
            <button
              className="guest-btn"
              onClick={() => {
                // ✅ Set BOTH localStorage AND sessionStorage immediately
                const authBufferData = {
                  userRole: "guest",
                  isAuthenticated: "true",
                  timestamp: Date.now()
                };
                
                localStorage.setItem("userRole", "guest");
                localStorage.setItem("isAuthenticated", "true");
                
                // Session storage as immediate buffer
                sessionStorage.setItem("authBuffer", JSON.stringify(authBufferData));
                
                // Navigate immediately
                navigate("/chat", { replace: true });
              }}
              disabled={isLoading}
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