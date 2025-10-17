import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { getCurrentSession } from "./auth.js";

const ProtectedRoute = ({ children, requireAuth = true }) => {
  // ✅ Initialize with synchronous checks IMMEDIATELY
  const getInitialAuth = () => {
    // ✅ CHECK: If logout is in progress, deny all auth
    if (sessionStorage.getItem("logoutInProgress") === "true") {
      console.log("🚪 Logout in progress, denying auth");
      return {
        isAuthenticated: false,
        userRole: null,
        needsAsyncCheck: false
      };
    }
    
    // Check sessionStorage buffer FIRST (synchronous)
    const authBuffer = sessionStorage.getItem("authBuffer");
    if (authBuffer) {
      try {
        const bufferData = JSON.parse(authBuffer);
        const age = Date.now() - bufferData.timestamp;
        
        // ✅ Buffer expires after 5 seconds
        if (age < 5000) {
          console.log("✅ [SYNC] Using sessionStorage buffer (age: " + age + "ms)");
          return {
            isAuthenticated: true,
            userRole: bufferData.userRole,
            needsAsyncCheck: false
          };
        } else {
          console.log("⏰ Auth buffer expired, clearing...");
          sessionStorage.removeItem("authBuffer");
        }
      } catch (e) {
        console.error("❌ Error parsing auth buffer:", e);
        sessionStorage.removeItem("authBuffer");
      }
    }
    
    // Check localStorage (synchronous)
    const localAuth = localStorage.getItem("isAuthenticated");
    const role = localStorage.getItem("userRole");
    
    if (localAuth === "true" && role) {
      console.log("✅ [SYNC] Using localStorage (role: " + role + ")");
      return {
        isAuthenticated: true,
        userRole: role,
        needsAsyncCheck: false
      };
    }
    
    console.log("❌ [SYNC] No valid auth found, need async check");
    // Not authenticated yet, need async check
    return {
      isAuthenticated: false,
      userRole: null,
      needsAsyncCheck: true
    };
  };

  const initialState = getInitialAuth();
  
  const [isAuthenticated, setIsAuthenticated] = useState(initialState.isAuthenticated);
  const [userRole, setUserRole] = useState(initialState.userRole);
  const [loading, setLoading] = useState(initialState.needsAsyncCheck);

  useEffect(() => {
    // If we already have auth from sync check, skip async check
    if (!initialState.needsAsyncCheck) {
      console.log("✅ Already authenticated from sync check, skipping async");
      return;
    }

    const checkAuth = async () => {
      try {
        console.log("🔍 Running async Supabase check...");
        const session = await getCurrentSession();

        if (session) {
          console.log("✅ Authenticated via Supabase session");
          setIsAuthenticated(true);
          
          // Update localStorage
          const email = session.user?.email;
          if (email && !localStorage.getItem("userRole")) {
            localStorage.setItem("isAuthenticated", "true");
            localStorage.setItem("userEmail", email);
          }
        } else {
          console.log("❌ Not authenticated");
          setIsAuthenticated(false);
        }
      } catch (error) {
        console.error("❌ Auth check error:", error);
        setIsAuthenticated(false);
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, [initialState.needsAsyncCheck]);

  // ✅ Show loading state only if we need async check
  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100vh",
          background: "var(--bg-primary, #f8f9fa)",
        }}
      >
        <div style={{ textAlign: "center" }}>
          <div style={{ 
            width: "40px", 
            height: "40px", 
            border: "4px solid #e0e0e0",
            borderTop: "4px solid #007bff",
            borderRadius: "50%",
            animation: "spin 1s linear infinite",
            margin: "0 auto 16px"
          }} />
          <div style={{ color: "#666" }}>Loading...</div>
        </div>
        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  // 🧩 Case 1: Needs authentication but not authenticated → Go to login
  if (requireAuth && !isAuthenticated) {
    console.log("🚫 Not authenticated, redirecting to /login");
    return <Navigate to="/login" replace />;
  }

  // 🧩 Case 2: At login screen but already logged in (not guest) → Go to chat
  if (!requireAuth && isAuthenticated && userRole !== "guest") {
    console.log("✅ Already authenticated, redirecting to /chat");
    return <Navigate to="/chat" replace />;
  }

  // 🧩 Case 3: Allow access
  console.log("✅ Access granted");
  return children;
};

export default ProtectedRoute;