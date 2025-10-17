import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { getCurrentSession } from "./auth.js";

const ProtectedRoute = ({ children, requireAuth = true }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(null);
  const [userRole, setUserRole] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const session = await getCurrentSession();
        const localAuth = localStorage.getItem("isAuthenticated");
        const role = localStorage.getItem("userRole");

        setUserRole(role);

        // ✅ Authenticated if Supabase session exists OR local flag is true
        if (session || localAuth === "true") {
          setIsAuthenticated(true);
        } else {
          setIsAuthenticated(false);
        }
      } catch (error) {
        console.error("Auth check error:", error);
        setIsAuthenticated(false);
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100vh",
        }}
      >
        <div>Loading...</div>
      </div>
    );
  }

  // 🧩 Case 1: Needs authentication but not authenticated → Go to login
  if (requireAuth && !isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // 🧩 Case 2: At login screen but already logged in (not guest) → Go to chat
  if (!requireAuth && isAuthenticated && userRole !== "guest") {
    return <Navigate to="/chat" replace />;
  }

  // 🧩 Case 3: Guests can stay on login (until they press "Continue as Guest")
  return children;
};

export default ProtectedRoute;
