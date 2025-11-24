//ProtectedRoute.jsx
import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { getCurrentSession } from "./auth.js";

const ProtectedRoute = ({ children, requireAuth = true }) => {
  // ✅ Initialize with synchronous checks FIRST for instant navigation
  const getInitialAuth = () => {
    console.log("🔍 [ProtectedRoute] getInitialAuth called");
    
    // CHECK: If logout is in progress, deny all auth
    if (sessionStorage.getItem("logoutInProgress") === "true") {
      console.log("🚪 Logout in progress, denying auth");
      return {
        isAuthenticated: false,
        userRole: null,
        needsVerification: false
      };
    }
    
    // Check sessionStorage buffer FIRST (synchronous, fresh from login)
    const authBuffer = sessionStorage.getItem("authBuffer");
    console.log("📦 authBuffer:", authBuffer);
    
    if (authBuffer) {
      try {
        const bufferData = JSON.parse(authBuffer);
        const age = Date.now() - bufferData.timestamp;
        
        console.log("⏱️ Buffer age:", age, "ms");
        
        // Buffer valid for 10 seconds (extended from 5)
        if (age < 10000) {
          console.log("✅ [SYNC] Using fresh buffer - INSTANT AUTH", bufferData);
          return {
            isAuthenticated: true,
            userRole: bufferData.userRole,
            needsVerification: bufferData.userRole !== "admin" && bufferData.userRole !== "guest"
          };
        } else {
          console.log("⏰ Buffer expired");
          sessionStorage.removeItem("authBuffer");
        }
      } catch (e) {
        console.error("❌ Error parsing buffer:", e);
        sessionStorage.removeItem("authBuffer");
      }
    }
    
    // Check localStorage for existing session (page refresh case)
    const storedAuth = localStorage.getItem("isAuthenticated");
    const storedRole = localStorage.getItem("userRole");
    
    console.log("💾 localStorage check:", { storedAuth, storedRole });
    
    if (storedAuth === "true" && storedRole) {
      console.log("✅ [SYNC] Using localStorage");
      return {
        isAuthenticated: true,
        userRole: storedRole,
        needsVerification: storedRole !== "admin" && storedRole !== "guest"
      };
    }
    
    // No auth found - need to show loading and verify
    console.log("❌ [SYNC] No auth found");
    return {
      isAuthenticated: false,
      userRole: null,
      needsVerification: true
    };
  };

  const initialState = getInitialAuth();
  
  const [isAuthenticated, setIsAuthenticated] = useState(initialState.isAuthenticated);
  const [userRole, setUserRole] = useState(initialState.userRole);
  const [loading, setLoading] = useState(false); // Start with false, only show if needed

  useEffect(() => {
    // Skip verification completely for admin and guest
    if (initialState.userRole === "admin" || initialState.userRole === "guest") {
      console.log("⏭️ Skipping verification for admin/guest");
      setLoading(false);
      return;
    }

    // Skip verification if not needed
    if (!initialState.needsVerification) {
      console.log("⏭️ Skipping verification (not needed)");
      setLoading(false);
      return;
    }

    // Background verification for Supabase users
    const verifyAuth = async () => {
      console.log("=== BACKGROUND VERIFICATION START ===");
      
      // Don't show loading if we already have instant auth
      if (!initialState.isAuthenticated) {
        setLoading(true);
      }
      
      try {
        console.log("🔍 Calling getCurrentSession...");
        const session = await getCurrentSession();
        console.log("📥 Session result:", session ? "Valid" : "Invalid");

        if (session && session.user) {
          console.log("✅ Valid Supabase session:", session.user.email);
          
          const storedEmail = localStorage.getItem("userEmail");
          const storedRole = localStorage.getItem("userRole");
          
          console.log("💾 Stored data:", { storedEmail, storedRole });
          
          // Verify stored data matches session
          if (storedEmail === session.user.email && storedRole) {
            console.log("✅ Verification passed");
            setIsAuthenticated(true);
            setUserRole(storedRole);
          } else {
            console.log("⚠️ Mismatch detected, clearing storage");
            localStorage.clear();
            sessionStorage.clear();
            setIsAuthenticated(false);
            setUserRole(null);
          }
        } else {
          console.log("❌ No valid session");
          
          // Only clear if we're past the buffer window
          const authBuffer = sessionStorage.getItem("authBuffer");
          if (!authBuffer) {
            console.log("🧹 Clearing storage (no buffer)");
            localStorage.clear();
            sessionStorage.clear();
            setIsAuthenticated(false);
            setUserRole(null);
          } else {
            console.log("⏳ Keeping auth (buffer still valid)");
          }
        }
      } catch (error) {
        console.error("❌ Verification error:", error);
        
        // Don't clear on error if we have instant auth
        if (!initialState.isAuthenticated) {
          localStorage.clear();
          sessionStorage.clear();
          setIsAuthenticated(false);
          setUserRole(null);
        }
      } finally {
        setLoading(false);
        console.log("=== BACKGROUND VERIFICATION END ===");
      }
    };

    // Small delay to let Supabase session settle
    const timer = setTimeout(verifyAuth, 100);
    return () => clearTimeout(timer);
  }, [initialState.isAuthenticated, initialState.needsVerification]);

  // ✅ Show loading only if needed
  if (loading) {
    console.log("⏳ Showing loading screen");
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
          <div style={{ color: "#666" }}>Verifying...</div>
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

  console.log("🎯 Render decision:", { requireAuth, isAuthenticated, userRole });

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