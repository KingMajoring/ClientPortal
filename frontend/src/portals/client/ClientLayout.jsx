import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { Icon } from "../../shared/components/Icon";
import { NotificationsBell } from "../../shared/components/NotificationsBell";

export function ClientLayout() {
  const { user, logout } = useAuth();
  const branding = user?.client_company;
  const initials = user ? `${user.first_name?.[0] || ""}${user.last_name?.[0] || ""}`.toUpperCase() : "";
  const style = branding?.primary_color ? { "--brand-color": branding.primary_color } : {};

  return (
    <div className="portal-shell" style={style}>
      <aside className="sidebar">
        <div className="sidebar-brand">
          {branding?.logo_path ? (
            <img className="sidebar-brand-icon" src={branding.logo_path} alt={branding.name} style={{ objectFit: "cover" }} />
          ) : (
            <div className="sidebar-brand-icon">
              <Icon name="key" size={18} />
            </div>
          )}
          <div className="sidebar-brand-text">
            <h1>{branding?.name || "Client Portal"}</h1>
            <span>WGTK Client Portal</span>
          </div>
        </div>

        <NavLink to="/portal/enquiries/new" className="button" style={{ justifyContent: "center" }}>
          <Icon name="plus" size={16} />
          Raise enquiry
        </NavLink>

        <nav className="sidebar-nav">
          <NavLink to="/portal/enquiries">
            <Icon name="inbox" size={18} />
            My enquiries
          </NavLink>
          <NavLink to="/portal/dashboard">
            <Icon name="chart" size={18} />
            Dashboard
          </NavLink>
          {user?.role === "CLIENT_ADMIN" && (
            <NavLink to="/portal/company">
              <Icon name="settings" size={18} />
              Company
            </NavLink>
          )}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-user">
            <div className="sidebar-avatar">{initials}</div>
            <div>
              <div className="sidebar-user-name">{user ? `${user.first_name} ${user.last_name}` : ""}</div>
              <div className="sidebar-user-role">{user?.role === "CLIENT_ADMIN" ? "Admin" : "User"}</div>
            </div>
          </div>
          <button className="sidebar-signout" onClick={logout}>
            <Icon name="logout" size={16} />
            Sign out
          </button>
        </div>
      </aside>

      <div className="portal-main">
        <div className="topbar">
          <NotificationsBell />
        </div>
        <main className="portal-content">
          <Outlet />
        </main>
        <footer className="powered-by">Powered by WGTK</footer>
      </div>
    </div>
  );
}
