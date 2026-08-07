import { Link } from "react-router-dom";

export function LandingPage() {
  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>WGTK Client Portal</h1>
        <p>Choose how you'd like to sign in:</p>
        <Link className="button" to="/staff/login">
          WGTK Staff Login
        </Link>
        <Link className="button" to="/portal/login">
          Client Portal Login
        </Link>
      </div>
      <footer className="powered-by">Powered by WGTK</footer>
    </div>
  );
}
