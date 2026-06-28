import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext";

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        height: "100vh",
        background: "#f6faf4",
        color: "#173b24",
        fontFamily: "sans-serif"
      }}>
        <div style={{ textAlign: "center" }}>
          <span style={{ fontSize: "40px" }}>🌾</span>
          <p style={{ marginTop: "12px", fontWeight: "bold" }}>Verifying access state...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    // Redirect to login page but save the current location they were trying to access
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}
