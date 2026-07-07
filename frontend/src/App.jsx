import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import Marketplace from "./pages/Marketplace";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Assistant from "./pages/Assistant";
import { AuthProvider } from "./lib/AuthContext";
import { CartProvider } from "./lib/CartContext";
import ProtectedRoute from "./lib/ProtectedRoute";

export default function App() {
  return (
    <AuthProvider>
      <CartProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/"            element={<Home />} />
            <Route path="/marketplace" element={<Marketplace />} />
            <Route path="/login"       element={<Login />} />
            <Route path="/signup"      element={<Signup />} />
            <Route path="/assistant"  element={<Assistant />} />
            
            {/* Protected dashboard route structure */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <div style={{ padding: "40px", textAlign: "center", fontFamily: "sans-serif" }}>
                    <h2>Farmer Dashboard (Protected)</h2>
                    <p>Welcome! This dashboard is secured by Supabase Auth.</p>
                    <a href="/" style={{ color: "#2f7d32", fontWeight: "bold" }}>Go back home</a>
                  </div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </BrowserRouter>
      </CartProvider>
    </AuthProvider>
  );
}