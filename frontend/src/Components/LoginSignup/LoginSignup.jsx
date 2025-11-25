import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { loginUser, getUserRole } from "../../utils/auth";
import { toast } from "sonner";
import { Eye, EyeOff } from "lucide-react"; // ✅ ADD: Lucide icons
import "react-toastify/dist/ReactToastify.css";
import "./LoginSignup.css";

// ✅ Schema for validation
const loginSchema = z.object({
  email: z.email("Invalid email address"),
  password: z.string().min(6, "Password must be at least 6 characters"),
});

const Login = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [showPasswordChangeAlert, setShowPasswordChangeAlert] = useState(false);
  const [newUserEmail, setNewUserEmail] = useState("");
  const [showPassword, setShowPassword] = useState(false); 

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(loginSchema),
  });

  // ✅ Toggle password visibility
   const togglePasswordVisibility = () => {
    setShowPassword(!showPassword);
  };

  // ✅ COMPLETELY FIXED: Guest login with comprehensive cleanup
  const handleGuestLogin = () => {
    if (isLoading) return;
    
    setIsLoading(true);
    console.log("🎭 Starting FRESH guest login process...");

    const performPreLoginCleanup = () => {
      // Clear all storage
      localStorage.clear();
      sessionStorage.clear();
      
      // Force clear any residual data
      Object.keys(localStorage).forEach(key => localStorage.removeItem(key));
      Object.keys(sessionStorage).forEach(key => sessionStorage.removeItem(key));
      
      console.log("✅ Pre-login cleanup completed");
    };

    try {
      // ✅ Clean up everything first
      performPreLoginCleanup();
      
      // ✅ Create FRESH guest session data
      const guestSessionId = `guest-${Date.now()}`;
      const authBufferData = {
        userRole: "guest",
        isAuthenticated: "true",
        timestamp: Date.now(),
        sessionId: guestSessionId,
        isFresh: true
      };

      localStorage.setItem("userRole", "guest");
      localStorage.setItem("isAuthenticated", "true");
      localStorage.setItem("currentSessionId", guestSessionId);
      
      sessionStorage.setItem("authBuffer", JSON.stringify(authBufferData));

      console.log("✅ Fresh guest authentication set:", {
        sessionId: guestSessionId,
        userRole: localStorage.getItem("userRole"),
        isAuthenticated: localStorage.getItem("isAuthenticated")
      });

      const welcomeMessages = [{
        text: "Hello! Welcome to Samriddhi ChatBot. Ask me anything.",
        sender: "bot",
        timestamp: new Date().toISOString()
      }];
      
      localStorage.setItem(`guest_messages_${guestSessionId}`, JSON.stringify(welcomeMessages));

      // ✅ Use shadcn/sonner toast for success
      toast.success("Starting guest session...");
      
      // ✅ Use hard navigation instead of React Router navigation
      console.log("🚀 Performing hard navigation to chat...");
      setTimeout(() => {
        window.location.href = "/chat";
      }, 100);

    } catch (error) {
      console.error("❌ Error in guest login:", error);
      // ✅ Use shadcn/sonner toast for error
      toast.error("Failed to start guest session. Please try again.");
      setIsLoading(false);
    }
  };

  const onSubmit = async (data) => {
    const { email, password } = data;
    setIsLoading(true);
    
    const loadingToast = toast.loading("Signing you in...");
    
    try {
      sessionStorage.removeItem("authBuffer");

      if (email === import.meta.env.VITE_ADMIN_EMAIL && password === import.meta.env.VITE_ADMIN_PASSWORD) {
        Object.keys(localStorage).forEach(key => {
          if (key.startsWith('guest_messages_') || key.startsWith('guest-')) {
            localStorage.removeItem(key);
          }
        });

        const authData = {
          userRole: "admin",
          userEmail: email,
          isAuthenticated: "true",
          timestamp: Date.now(),
        };

        localStorage.setItem("userRole", "admin");
        localStorage.setItem("adminEmail", email);
        localStorage.setItem("isAuthenticated", "true");
        sessionStorage.setItem("authBuffer", JSON.stringify(authData));

        console.log("✅ Admin auth set, navigating...");
        toast.dismiss(loadingToast);
        toast.success("Admin login successful!");
        navigate("/admin", { replace: true });
        setIsLoading(false);
        return;
      }

      // Regular user login with Supabase
      console.log("🔐 Attempting Supabase login for:", email);
      const { data: authData, error } = await loginUser(email, password);

      // ✅ Handle Supabase error response - FIXED FOR BACKEND RESPONSE
      if (error) {
        console.error("❌ Supabase Login Failed:", error);
        toast.dismiss(loadingToast);
        sessionStorage.removeItem("authBuffer");
        
        let errorMessage = "Invalid email or password. Please try again.";
        
        // ✅ SPECIFIC HANDLING FOR BACKEND RESPONSE
        if (error.code === "invalid_credentials" || error.message?.includes("Invalid login credentials")) {
          errorMessage = "Invalid email or password.";
        } else if (error.message?.includes("Email not confirmed")) {
          errorMessage = "Please verify your email address before logging in.";
        } else if (error.message?.includes("Too many requests")) {
          errorMessage = "Too many login attempts. Please try again later.";
        }
        
        toast.error("Login Failed", {
          description: errorMessage,
          duration: 4000,
        });
        
        setIsLoading(false);
        return;
      }

      // ✅ Check if authData exists and has user - SHOW INVALID CREDENTIALS INSTEAD
      if (!authData?.user) {
        console.error("❌ No user data received from Supabase");
        toast.dismiss(loadingToast);
        toast.error("Login Failed", {
          description: "Invalid email or password.",
          duration: 4000,
        });
        setIsLoading(false);
        return;
      }

      console.log("✅ Supabase login successful, fetching role...");

      // Clear guest data
      Object.keys(localStorage).forEach(key => {
        if (key.startsWith('guest_messages_') || key.startsWith('guest-')) {
          localStorage.removeItem(key);
        }
      });

      // Get user role
      const userRole = await getUserRole(email);
      console.log("✅ User role detected:", userRole);

      // Check if role was found - SHOW INVALID CREDENTIALS INSTEAD
      if (!userRole || userRole === "guest") {
        console.error("❌ No valid role found for user");
        toast.dismiss(loadingToast);
        toast.error("Login Failed", {
          description: "Invalid email or password.",
          duration: 4000,
        });
        sessionStorage.removeItem("authBuffer");
        setIsLoading(false);
        return;
      }

      // Set authentication data
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
      sessionStorage.setItem("authBuffer", JSON.stringify(authBufferData));

      console.log("✅ Auth data set:", authBufferData);

      // Check if user needs to change password
      let hasChangedPassword = localStorage.getItem(`password_changed_${email}`);

      // If not in localStorage, check database
      if (!hasChangedPassword) {
        try {
          const tableName = userRole === "student" ? "students_data" : 
                           userRole === "teacher" ? "teachers_data" : null;

          if (tableName) {
            const response = await fetch(
              "http://localhost:5000/api/check-password-changed",
              {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, table: tableName }),
              }
            );

            if (response.ok) {
              const data = await response.json();
              if (data.password_changed) {
                localStorage.setItem(`password_changed_${email}`, "true");
                hasChangedPassword = "true";
              }
            }
          }
        } catch (error) {
          console.log("⚠️ Could not check database, using localStorage only");
        }
      }

      // FINAL SUCCESS PATH - Always dismiss loading toast
      toast.dismiss(loadingToast);

      if (!hasChangedPassword) {
        setNewUserEmail(email);
        setShowPasswordChangeAlert(true);
        setIsLoading(false);
      } else {
        toast.success(`Welcome back!`, {
          description: `Logged in successfully as ${userRole}`,
          duration: 3000,
        });
        navigate("/chat", { replace: true });
        setIsLoading(false);
      }

    } catch (error) {
      // CATCH ALL ERRORS - Always dismiss loading toast
      console.error("💥 Login component catch block error:", error);
      toast.dismiss(loadingToast);
      
      let errorMessage = "Something went wrong. Please check your connection.";
      
      if (error.message?.includes("Failed to fetch") || error.message?.includes("Network")) {
        errorMessage = "Network error. Please check your internet connection.";
      }
      
      toast.error("Connection Error", {
        description: errorMessage,
        duration: 4000,
      });
      
      sessionStorage.removeItem("authBuffer");
      setIsLoading(false);
    }
  };

  const handleSkipPasswordChange = () => {
    setShowPasswordChangeAlert(false);
    
    // Use shadcn/sonner toast
    toast.success("Login successful!");
    
    navigate("/chat", { replace: true });
  };

  const handleGoToChangePassword = () => {
    setShowPasswordChangeAlert(false);
    // Mark that user should see change password modal
    sessionStorage.setItem("show_password_modal", "true");
    
    // Use shadcn/sonner toast
    toast.success("Login successful! Please change your password.");
    
    navigate("/chat", { replace: true });
  };

  return (
    <div className="login-container">
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
          
          {/* ✅ UPDATED: Password field with Lucide eye icons */}
          <div className="input-group password-input-group">
            <div className="password-input-wrapper">
              <input
                type={showPassword ? "text" : "password"}
                placeholder="Password"
                {...register("password")}
                className="login-input password-input"
                disabled={isLoading}
              />
              <button
                type="button"
                className="password-toggle-btn"
                onClick={togglePasswordVisibility}
                disabled={isLoading}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? (
                  // Eye off icon (password hidden)
                  <Eye size={20} className="password-toggle-icon" />
                ) : (
                  // Eye icon (password visible)
                  <EyeOff size={20} className="password-toggle-icon" />
                )}
              </button>
            </div>
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
              onClick={handleGuestLogin}
              disabled={isLoading}
            >
              {isLoading ? "Loggin in..." : "Continue as Guest"}
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

