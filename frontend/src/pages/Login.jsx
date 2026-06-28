import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import AuthLayout from "../components/AuthLayout";
import { supabase } from "../lib/supabase";
import "../components/AuthForm.css";
import "./Login.css";

/* ————————————————————————————————————————
   Validation helpers
   ———————————————————————————————————————— */
const isValidEmail = (v) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim());

const BENEFITS = [
  { icon: "🧺", text: "Sell farm products directly to buyers" },
  { icon: "🚜", text: "Rent agricultural equipment near you" },
  { icon: "🤖", text: "Get AI-powered marketplace help" },
];

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: "", password: "", remember: false });
  const [errors, setErrors] = useState({});
  const [showPw, setShowPw] = useState(false);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  const redirectPath = location.state?.from?.pathname || "/marketplace";

  /* ——— Per-field change ——— */
  function handleChange(e) {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({ ...prev, [name]: type === "checkbox" ? checked : value }));
    // Clear errors on edit
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: "" }));
    setFormError("");
  }

  /* ——— Validate ——— */
  function validate() {
    const errs = {};
    if (!form.email.trim()) {
      errs.email = "Email address is required.";
    } else if (!isValidEmail(form.email)) {
      errs.email = "Please enter a valid email address.";
    }
    if (!form.password) {
      errs.password = "Password is required.";
    }
    return errs;
  }

  /* ——— Submit ——— */
  async function handleSubmit(e) {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length > 0) {
      setErrors(errs);
      return;
    }

    setSubmitting(true);
    setFormError("");

    try {
      const { error } = await supabase.auth.signInWithPassword({
        email: form.email.trim(),
        password: form.password,
      });

      if (error) {
        setFormError(error.message);
      } else {
        setSuccess(true);
        setTimeout(() => {
          navigate(redirectPath);
        }, 1500);
      }
    } catch (err) {
      setFormError("An unexpected error occurred. Please try again.");
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  }


  return (
    <AuthLayout benefits={BENEFITS}>
      <div className="auth-card">
        <h1 className="auth-card-title">Welcome back 👋</h1>
        <p className="auth-card-sub">
          Log in to your AgriConnect AI account to continue.
        </p>

        {/* ——— Success message ——— */}
        {success && (
          <div className="auth-success-box" role="alert">
            <span className="auth-success-icon">✅</span>
            <p>
              <strong>Login successful!</strong>
              Redirecting you to the marketplace...
            </p>
          </div>
        )}

        {!success && (
          <form onSubmit={handleSubmit} noValidate aria-label="Login form">
            {formError && (
              <div className="auth-form-error" role="alert">
                <span>⚠ {formError}</span>
              </div>
            )}

            {/* Email */}

            <div className="auth-field">
              <label htmlFor="login-email" className="auth-label">
                Email address <span aria-hidden="true">*</span>
              </label>
              <input
                id="login-email"
                type="email"
                name="email"
                className={`auth-input${errors.email ? " input-error" : ""}`}
                placeholder="you@example.com"
                value={form.email}
                onChange={handleChange}
                autoComplete="email"
                aria-describedby={errors.email ? "login-email-err" : undefined}
                aria-invalid={!!errors.email}
              />
              {errors.email && (
                <span id="login-email-err" className="auth-error-msg" role="alert">
                  ⚠ {errors.email}
                </span>
              )}
            </div>

            {/* Password */}
            <div className="auth-field">
              <label htmlFor="login-password" className="auth-label">
                Password <span aria-hidden="true">*</span>
              </label>
              <div className="auth-pw-wrap">
                <input
                  id="login-password"
                  type={showPw ? "text" : "password"}
                  name="password"
                  className={`auth-input${errors.password ? " input-error" : ""}`}
                  placeholder="Enter your password"
                  value={form.password}
                  onChange={handleChange}
                  autoComplete="current-password"
                  aria-describedby={errors.password ? "login-pw-err" : undefined}
                  aria-invalid={!!errors.password}
                />
                <button
                  type="button"
                  className="auth-pw-toggle"
                  onClick={() => setShowPw((v) => !v)}
                  aria-label={showPw ? "Hide password" : "Show password"}
                >
                  {showPw ? "🙈" : "👁️"}
                </button>
              </div>
              {errors.password && (
                <span id="login-pw-err" className="auth-error-msg" role="alert">
                  ⚠ {errors.password}
                </span>
              )}
            </div>

            {/* Remember me + Forgot password */}
            <div className="login-extras">
              <label className="auth-check-row" style={{ margin: 0 }}>
                <input
                  type="checkbox"
                  name="remember"
                  id="login-remember"
                  checked={form.remember}
                  onChange={handleChange}
                />
                <span className="auth-check-label">Remember me</span>
              </label>
              <a
                href="#forgot"
                className="login-forgot"
                onClick={(e) => {
                  e.preventDefault();
                  alert("Password reset coming soon.");
                }}
              >
                Forgot password?
              </a>
            </div>

            {/* Submit */}
            <button
              id="login-submit-btn"
              type="submit"
              className="auth-submit-btn"
              disabled={submitting}
              aria-busy={submitting}
            >
              {submitting ? "Signing in…" : "Log in to AgriConnect"}
            </button>

            <p className="auth-footer-text">
              Don&apos;t have an account?
              <Link to="/signup">Create one free →</Link>
            </p>
          </form>
        )}

        {/* After success – show a link back to home */}
        {success && (
          <p className="auth-footer-text" style={{ marginTop: 16 }}>
            <Link to="/">← Back to homepage</Link>
          </p>
        )}
      </div>
    </AuthLayout>
  );
}
