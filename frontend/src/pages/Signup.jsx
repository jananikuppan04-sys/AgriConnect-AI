import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AuthLayout from "../components/AuthLayout";
import { supabase } from "../lib/supabase";
import "../components/AuthForm.css";
import "./Signup.css";

/* ————————————————————————————————————————
   Constants
   ———————————————————————————————————————— */
const BENEFITS = [
  { icon: "🌾", text: "List your crops and farm produce" },
  { icon: "🛒", text: "Connect with verified buyers directly" },
  { icon: "📍", text: "Discover opportunities near your district" },
];

const ROLES = [
  { value: "", label: "Select your role…" },
  { value: "farmer", label: "🌾 Farmer / Seller" },
  { value: "buyer", label: "🛒 Buyer" },
  { value: "equipment", label: "🚜 Equipment Owner" },
];

const DISTRICTS = [
  "Chennai", "Coimbatore", "Cuddalore", "Dharmapuri",
  "Dindigul", "Erode", "Kancheepuram", "Kanyakumari",
  "Krishnagiri", "Madurai", "Nagapattinam", "Namakkal",
  "Nilgiris", "Perambalur", "Pudukkottai", "Ramanathapuram",
  "Salem", "Sivaganga", "Thanjavur", "Theni",
  "Thiruvallur", "Thiruvarur", "Thoothukudi", "Tiruchirappalli",
  "Tirunelveli", "Tiruppur", "Tiruvanamalai", "Vellore",
  "Villupuram", "Virudhunagar",
];

/* ————————————————————————————————————————
   Validation helpers
   ———————————————————————————————————————— */
const isValidEmail = (v) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim());
const isValidPhone  = (v) => /^[6-9]\d{9}$/.test(v.replace(/\s+/g, ""));

function validate(form) {
  const errs = {};

  if (!form.fullName.trim())       errs.fullName = "Full name is required.";
  if (!form.email.trim())          errs.email = "Email address is required.";
  else if (!isValidEmail(form.email)) errs.email = "Enter a valid email address.";
  if (!form.phone.trim())          errs.phone = "Phone number is required.";
  else if (!isValidPhone(form.phone)) errs.phone = "Enter a valid 10-digit Indian mobile number.";
  if (!form.role)                  errs.role = "Please select your role.";
  if (!form.district)              errs.district = "Please select your district.";
  if (!form.password)              errs.password = "Password is required.";
  else if (form.password.length < 8) errs.password = "Password must be at least 8 characters.";
  if (!form.confirmPassword)       errs.confirmPassword = "Please confirm your password.";
  else if (form.password !== form.confirmPassword)
                                   errs.confirmPassword = "Passwords do not match.";
  if (!form.terms)                 errs.terms = "You must accept the terms to continue.";

  return errs;
}

/* ————————————————————————————————————————
   Component
   ———————————————————————————————————————— */
export default function Signup() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    fullName: "", email: "", phone: "",
    password: "", confirmPassword: "",
    role: "", district: "", terms: false,
  });
  const [errors, setErrors]     = useState({});
  const [showPw, setShowPw]     = useState(false);
  const [showCpw, setShowCpw]   = useState(false);
  const [success, setSuccess]   = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  /* ——— Field change ——— */
  function handleChange(e) {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({ ...prev, [name]: type === "checkbox" ? checked : value }));
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: "" }));
    setFormError("");
  }

  /* ——— Submit ——— */
  async function handleSubmit(e) {
    e.preventDefault();
    const errs = validate(form);
    if (Object.keys(errs).length > 0) {
      setErrors(errs);
      // Scroll to first error
      const firstErrId = Object.keys(errs)[0];
      const el = document.getElementById(`signup-${firstErrId}`);
      if (el) el.focus();
      return;
    }

    setSubmitting(true);
    setFormError("");

    try {
      const { error } = await supabase.auth.signUp({
        email: form.email.trim(),
        password: form.password,
        options: {
          data: {
            full_name: form.fullName.trim(),
            phone: form.phone,
            role: form.role,
            district: form.district,
          }
        }
      });

      if (error) {
        setFormError(error.message);
      } else {
        setSuccess(true);
        setTimeout(() => {
          navigate("/login");
        }, 2500);
      }
    } catch (err) {
      setFormError("An unexpected error occurred. Please try again.");
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  }


  /* ——— Helper: renders an error span ——— */
  function ErrMsg({ field }) {
    return errors[field] ? (
      <span className="auth-error-msg" role="alert" id={`${field}-err`}>
        ⚠ {errors[field]}
      </span>
    ) : null;
  }

  return (
    <AuthLayout benefits={BENEFITS}>
      <div className="auth-card signup-card">
        <h1 className="auth-card-title">Create your account 🌱</h1>
        <p className="auth-card-sub">
          Join AgriConnect AI — it&apos;s free and takes less than 2 minutes.
        </p>

        {/* ——— Success ——— */}
        {success && (
          <div className="auth-success-box" role="alert">
            <span className="auth-success-icon">🎉</span>
            <p>
              <strong>Account created successfully!</strong>
              Check your email for confirmation, redirecting to login...
            </p>
          </div>
        )}

        {!success && (
          <form onSubmit={handleSubmit} noValidate aria-label="Signup form">
            {formError && (
              <div className="auth-form-error" role="alert">
                <span>⚠ {formError}</span>
              </div>
            )}

            {/* Full Name */}

            <div className="auth-field">
              <label htmlFor="signup-fullName" className="auth-label">
                Full name <span>*</span>
              </label>
              <input
                id="signup-fullName"
                type="text"
                name="fullName"
                className={`auth-input${errors.fullName ? " input-error" : ""}`}
                placeholder="e.g. Rajan Kumar"
                value={form.fullName}
                onChange={handleChange}
                autoComplete="name"
                aria-invalid={!!errors.fullName}
              />
              <ErrMsg field="fullName" />
            </div>

            {/* Email + Phone in a row */}
            <div className="auth-row">
              <div className="auth-field">
                <label htmlFor="signup-email" className="auth-label">
                  Email <span>*</span>
                </label>
                <input
                  id="signup-email"
                  type="email"
                  name="email"
                  className={`auth-input${errors.email ? " input-error" : ""}`}
                  placeholder="you@example.com"
                  value={form.email}
                  onChange={handleChange}
                  autoComplete="email"
                  aria-invalid={!!errors.email}
                />
                <ErrMsg field="email" />
              </div>
              <div className="auth-field">
                <label htmlFor="signup-phone" className="auth-label">
                  Phone <span>*</span>
                </label>
                <input
                  id="signup-phone"
                  type="tel"
                  name="phone"
                  className={`auth-input${errors.phone ? " input-error" : ""}`}
                  placeholder="9876543210"
                  value={form.phone}
                  onChange={handleChange}
                  autoComplete="tel"
                  maxLength={10}
                  aria-invalid={!!errors.phone}
                />
                <ErrMsg field="phone" />
              </div>
            </div>

            {/* Role + District in a row */}
            <div className="auth-row">
              <div className="auth-field">
                <label htmlFor="signup-role" className="auth-label">
                  Role <span>*</span>
                </label>
                <select
                  id="signup-role"
                  name="role"
                  className={`auth-select${errors.role ? " input-error" : ""}`}
                  value={form.role}
                  onChange={handleChange}
                  aria-invalid={!!errors.role}
                >
                  {ROLES.map((r) => (
                    <option key={r.value} value={r.value} disabled={r.value === ""}>
                      {r.label}
                    </option>
                  ))}
                </select>
                <ErrMsg field="role" />
              </div>
              <div className="auth-field">
                <label htmlFor="signup-district" className="auth-label">
                  District <span>*</span>
                </label>
                <select
                  id="signup-district"
                  name="district"
                  className={`auth-select${errors.district ? " input-error" : ""}`}
                  value={form.district}
                  onChange={handleChange}
                  aria-invalid={!!errors.district}
                >
                  <option value="" disabled>Select district…</option>
                  {DISTRICTS.map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
                <ErrMsg field="district" />
              </div>
            </div>

            {/* Password */}
            <div className="auth-field">
              <label htmlFor="signup-password" className="auth-label">
                Password <span>*</span>
              </label>
              <div className="auth-pw-wrap">
                <input
                  id="signup-password"
                  type={showPw ? "text" : "password"}
                  name="password"
                  className={`auth-input${errors.password ? " input-error" : ""}`}
                  placeholder="Minimum 8 characters"
                  value={form.password}
                  onChange={handleChange}
                  autoComplete="new-password"
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
              <ErrMsg field="password" />
              {/* Password strength bar */}
              {form.password && (
                <PasswordStrength password={form.password} />
              )}
            </div>

            {/* Confirm Password */}
            <div className="auth-field">
              <label htmlFor="signup-confirmPassword" className="auth-label">
                Confirm password <span>*</span>
              </label>
              <div className="auth-pw-wrap">
                <input
                  id="signup-confirmPassword"
                  type={showCpw ? "text" : "password"}
                  name="confirmPassword"
                  className={`auth-input${errors.confirmPassword ? " input-error" : ""}`}
                  placeholder="Re-enter your password"
                  value={form.confirmPassword}
                  onChange={handleChange}
                  autoComplete="new-password"
                  aria-invalid={!!errors.confirmPassword}
                />
                <button
                  type="button"
                  className="auth-pw-toggle"
                  onClick={() => setShowCpw((v) => !v)}
                  aria-label={showCpw ? "Hide confirm password" : "Show confirm password"}
                >
                  {showCpw ? "🙈" : "👁️"}
                </button>
              </div>
              <ErrMsg field="confirmPassword" />
            </div>

            {/* Terms checkbox */}
            <div style={{ marginBottom: errors.terms ? 4 : 24 }}>
              <label className="auth-check-row" style={{ margin: 0, alignItems: "flex-start" }}>
                <input
                  type="checkbox"
                  name="terms"
                  id="signup-terms"
                  checked={form.terms}
                  onChange={handleChange}
                  aria-invalid={!!errors.terms}
                />
                <span className="auth-check-label">
                  I agree to the{" "}
                  <a href="#terms" onClick={(e) => e.preventDefault()}>Terms of Service</a>
                  {" "}and{" "}
                  <a href="#privacy" onClick={(e) => e.preventDefault()}>Privacy Policy</a>
                  {" "}of AgriConnect AI.
                </span>
              </label>
              {errors.terms && (
                <span className="auth-error-msg" role="alert" style={{ marginTop: 6, display: "flex" }}>
                  ⚠ {errors.terms}
                </span>
              )}
            </div>

            {/* Submit */}
            <button
              id="signup-submit-btn"
              type="submit"
              className="auth-submit-btn"
              disabled={submitting}
              aria-busy={submitting}
            >
              {submitting ? "Creating account…" : "Create Free Account →"}
            </button>

            <p className="auth-footer-text">
              Already have an account?
              <Link to="/login">Log in →</Link>
            </p>
          </form>
        )}
      </div>
    </AuthLayout>
  );
}

/* ————————————————————————————————————————
   Password strength indicator
   ———————————————————————————————————————— */
function getStrength(pw) {
  let score = 0;
  if (pw.length >= 8)  score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  if (score <= 1) return { label: "Weak", color: "#e53935", pct: 25 };
  if (score <= 2) return { label: "Fair", color: "#fb8c00", pct: 50 };
  if (score <= 3) return { label: "Good", color: "#43a047", pct: 75 };
  return { label: "Strong", color: "#1b5e20", pct: 100 };
}

function PasswordStrength({ password }) {
  const { label, color, pct } = getStrength(password);
  return (
    <div className="pw-strength">
      <div className="pw-strength-bar-bg">
        <div
          className="pw-strength-bar-fill"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <span className="pw-strength-label" style={{ color }}>
        {label}
      </span>
    </div>
  );
}
