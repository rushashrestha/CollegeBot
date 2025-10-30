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
  const [showPasswordChangeAlert, setShowPasswordChangeAlert] = useState(false);
  const [newUserEmail, setNewUserEmail] = useState("");

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
          timestamp: Date.now(),
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
        if (!userRole || userRole === "guest") {
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
          timestamp: Date.now(),
        };

        localStorage.setItem("userRole", userRole);
        localStorage.setItem("userEmail", email);
        localStorage.setItem("isAuthenticated", "true");
        localStorage.setItem("supabase_user_id", authData.user.id);

        // Session storage as immediate buffer
        sessionStorage.setItem("authBuffer", JSON.stringify(authBufferData));

        console.log("✅ Auth data set:", authBufferData);

        // Check if user needs to change password (check database first, then localStorage)
        let hasChangedPassword = localStorage.getItem(
          `password_changed_${email}`
        );

        // If not in localStorage, check database
        if (!hasChangedPassword) {
          try {
            const tableName =
              userRole === "student"
                ? "students_data"
                : userRole === "teacher"
                ? "teachers_data"
                : null;

            if (tableName) {
              const response = await fetch(
                "http://localhost:5000/api/check-password-changed",
                {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ email, table: tableName }),
                }
              );

              const data = await response.json();
              if (data.password_changed) {
                // Update localStorage so we don't check again
                localStorage.setItem(`password_changed_${email}`, "true");
                hasChangedPassword = "true";
              }
            }
          } catch (error) {
            console.log("⚠️ Could not check database, using localStorage only");
          }
        }

        if (!hasChangedPassword) {
          // First time login - show password change alert
          setNewUserEmail(email);
          setShowPasswordChangeAlert(true);
          setIsLoading(false);
        } else {
          // Password already changed - proceed normally
          toast.success(`Login successful as ${userRole}!`);
          navigate("/chat", { replace: true });
          setIsLoading(false);
        }
      }
    } catch (error) {
      console.error("💥 Login component catch block error:", error);
      toast.error("Something went wrong. Please check your connection.");
      sessionStorage.removeItem("authBuffer");
      setIsLoading(false);
    }
  };

  const handleSkipPasswordChange = () => {
    setShowPasswordChangeAlert(false);
    toast.success(`Login successful!`);
    navigate("/chat", { replace: true });
  };

  const handleGoToChangePassword = () => {
    setShowPasswordChangeAlert(false);
    // Mark that user should see change password modal
    sessionStorage.setItem("show_password_modal", "true");
    toast.success(`Login successful! Please change your password.`);
    navigate("/chat", { replace: true });
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
                  timestamp: Date.now(),
                };

                localStorage.setItem("userRole", "guest");
                localStorage.setItem("isAuthenticated", "true");

                // Session storage as immediate buffer
                sessionStorage.setItem(
                  "authBuffer",
                  JSON.stringify(authBufferData)
                );

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
      {showPasswordChangeAlert && (
        <div className="password-alert-overlay">
          <div className="password-alert-modal">
            <div className="alert-icon">
              <svg
                width="64"
                height="64"
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <circle
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="#f59e0b"
                  strokeWidth="2"
                />
                <path
                  d="M12 8V12"
                  stroke="#f59e0b"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
                <circle cx="12" cy="16" r="1" fill="#f59e0b" />
              </svg>
            </div>
            <h2>Security Recommendation</h2>
            <p>
              You're logging in with a default password assigned by the admin.
              For your account security, we <strong>strongly recommend</strong>{" "}
              changing your password immediately.
            </p>
            <div className="alert-benefits">
              <div className="benefit-item">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M9 12L11 14L15 10"
                    stroke="#10b981"
                    strokeWidth="2"
                    strokeLinecap="round"
                  />
                  <circle
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="#10b981"
                    strokeWidth="2"
                  />
                </svg>
                <span>Protect your personal information</span>
              </div>
              <div className="benefit-item">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M9 12L11 14L15 10"
                    stroke="#10b981"
                    strokeWidth="2"
                    strokeLinecap="round"
                  />
                  <circle
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="#10b981"
                    strokeWidth="2"
                  />
                </svg>
                <span>Prevent unauthorized access</span>
              </div>
              <div className="benefit-item">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M9 12L11 14L15 10"
                    stroke="#10b981"
                    strokeWidth="2"
                    strokeLinecap="round"
                  />
                  <circle
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="#10b981"
                    strokeWidth="2"
                  />
                </svg>
                <span>Secure your academic data</span>
              </div>
            </div>
            <div className="alert-actions">
              <button
                className="change-now-btn"
                onClick={handleGoToChangePassword}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <rect
                    x="3"
                    y="11"
                    width="18"
                    height="11"
                    rx="2"
                    stroke="currentColor"
                    strokeWidth="2"
                  />
                  <path
                    d="M7 11V7C7 5.67392 7.52678 4.40215 8.46447 3.46447C9.40215 2.52678 10.6739 2 12 2C13.3261 2 14.5979 2.52678 15.5355 3.46447C16.4732 4.40215 17 5.67392 17 7V11"
                    stroke="currentColor"
                    strokeWidth="2"
                  />
                </svg>
                Change Password Now
              </button>
              <button className="skip-btn" onClick={handleSkipPasswordChange}>
                I'll do it later
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Login;
