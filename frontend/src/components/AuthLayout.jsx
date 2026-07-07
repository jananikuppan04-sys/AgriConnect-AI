import { Link } from "react-router-dom";
import "./AuthLayout.css";

/**
 * AuthLayout
 * Shared two-column wrapper used by both Login and Signup pages.
 *
 * Props:
 *  benefits  – array of { icon, text } shown in the left panel
 *  children  – the form content rendered in the right panel
 */
export default function AuthLayout({ benefits = [], children }) {
  return (
    <div className="auth-page">
      {/* ——— Left: branded panel ——— */}
      <aside className="auth-panel">
        <Link to="/" className="auth-logo">
          <span className="auth-logo-icon">🌾</span>
          <span>AgriConnect AI</span>
        </Link>

        <div className="auth-panel-body">
          <p className="auth-panel-eyebrow">SMART AGRICULTURE MARKETPLACE</p>
          <h2 className="auth-panel-heading">
            Grow your farm.<br />
            <span>Reach more buyers.</span>
          </h2>
          <p className="auth-panel-sub">
            Join thousands of farmers, buyers, and equipment owners already
            using AgriConnect AI across Tamil Nadu.
          </p>

          {benefits.length > 0 && (
            <ul className="auth-benefits">
              {benefits.map((b, i) => (
                <li key={i} className="auth-benefit-item">
                  <span className="auth-benefit-icon">{b.icon}</span>
                  <span>{b.text}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* decorative elements */}
        <div className="auth-panel-deco" aria-hidden="true">🌿</div>
        <div className="auth-panel-deco2" aria-hidden="true">🌱</div>
      </aside>

      {/* ——— Right: form panel ——— */}
      <main className="auth-form-panel">
        {children}
      </main>
    </div>
  );
}
