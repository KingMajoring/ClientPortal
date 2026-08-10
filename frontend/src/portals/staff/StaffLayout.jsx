import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { Icon } from "../../shared/components/Icon";
import { NotificationsBell } from "../../shared/components/NotificationsBell";

const NAV_ITEMS = [
  { to: "/staff/enquiries", label: "Enquiries", icon: "inbox" },
  { to: "/staff/clients", label: "Clients", icon: "building" },
  { to: "/staff/users", label: "Users", icon: "users", adminOnly: true },
  { to: "/staff/dashboard", label: "Dashboard", icon: "chart" },
];

export function StaffLayout() {
  const { user, logout } = useAuth();
  const initials = user ? `${user.first_name?.[0] || ""}${user.last_name?.[0] || ""}`.toUpperCase() : "";

  return (
    <div className="portal-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="sidebar-brand-icon">
            <Icon name="key" size={18} />
          </div>
          <div className="sidebar-brand-text">
            <h1>WGTK</h1>
            <span>Staff Portal</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          {NAV_ITEMS.filter((item) => !item.adminOnly || user?.role === "WGTK_ADMIN").map((item) => (
            <NavLink key={item.to} to={item.to}>
              <Icon name={item.icon} size={18} />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-user">
            <div className="sidebar-avatar">{initials}</div>
            <div>
              <div className="sidebar-user-name">{user ? `${user.first_name} ${user.last_name}` : ""}</div>
              <div className="sidebar-user-role">{user?.role === "WGTK_ADMIN" ? "Admin" : "Staff"}</div>
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
