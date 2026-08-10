import { Link } from "react-router-dom";
import { Icon } from "./shared/components/Icon";

export function LandingPage() {
  return (
    <div className="auth-page">
      <div className="auth-card" style={{ alignItems: "center", textAlign: "center" }}>
        <div className="sidebar-brand-icon" style={{ width: 44, height: 44 }}>
          <Icon name="key" size={22} />
        </div>
        <h1>WGTK Client Portal</h1>
        <p>Choose how you'd like to sign in</p>
        <Link className="button btn-block" to="/staff/login">
          WGTK Staff Login
        </Link>
        <Link className="button btn-secondary btn-block" to="/portal/login">
          Client Portal Login
        </Link>
      </div>
      <footer className="powered-by">Powered by WGTK</footer>
    </div>
  );
}
