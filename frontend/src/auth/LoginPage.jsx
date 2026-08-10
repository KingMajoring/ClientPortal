import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { Icon } from "../shared/components/Icon";
import { useAuth } from "./AuthContext";

export function LoginPage({ title, allowedRoles, homePath, otherPortalHint }) {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  if (user && allowedRoles.includes(user.role)) {
    return <Navigate to={homePath} replace />;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const loggedInUser = await login(email, password);
      if (!allowedRoles.includes(loggedInUser.role)) {
        setError(otherPortalHint);
        return;
      }
      navigate(homePath, { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="sidebar-brand-icon" style={{ width: 40, height: 40 }}>
          <Icon name="key" size={20} />
        </div>
        <h1>{title}</h1>
        <form onSubmit={handleSubmit}>
          <label>
            Email
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>
          <label>
            Password
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </label>
          {error && <p className="form-error">{error}</p>}
          <button type="submit" className="btn-block" disabled={submitting}>
            {submitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </div>
      <footer className="powered-by">Powered by WGTK</footer>
    </div>
  );
}
