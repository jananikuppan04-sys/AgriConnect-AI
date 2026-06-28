import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/AuthContext";
import { useCart } from "../lib/CartContext";
import "./Navbar.css";

export default function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, signOut } = useAuth();
  const { cartCount } = useCart();

  const handleLogout = async () => {
    try {
      await signOut();
      navigate("/");
    } catch (error) {
      console.error("Error signing out:", error);
    }
  };

  return (
    <nav className="navbar">
      <Link to="/" className="logo" style={{ textDecoration: "none" }}>
        <span className="logo-mark">🌾</span>
        <span>AgriConnect AI</span>
      </Link>

      <div className="nav-links">
        <Link
          to="/marketplace"
          className={location.pathname === "/marketplace" ? "nav-active" : ""}
        >
          Marketplace
        </Link>
        <a href={location.pathname === "/" ? "#rentals" : "/#rentals"}>
          Rentals
        </a>
        <a href={location.pathname === "/" ? "#features" : "/#features"}>
          How it works
        </a>
        <Link
          to="/assistant"
          className={location.pathname === "/assistant" ? "nav-active" : ""}
        >
          🤖 AI Assistant
        </Link>
      </div>


      <div className="nav-actions">
        {/* Cart indicator badge */}
        <span className="nav-cart-badge" title="Items in your cart">
          🛒 <span className="cart-count-pill">{cartCount}</span>
        </span>

        {user ? (
          <>
            <span className="user-email-display" title={user.email}>
              👤 {user.email.split("@")[0]}
            </span>
            <button className="login-btn" onClick={handleLogout}>
              Log out
            </button>
            <Link to="/dashboard">
              <button className="primary-btn">Dashboard</button>
            </Link>
          </>
        ) : (
          <>
            <Link to="/login">
              <button className="login-btn">Log in</button>
            </Link>
            <Link to="/signup">
              <button className="primary-btn">Join as Farmer</button>
            </Link>
          </>
        )}
      </div>
    </nav>
  );
}

