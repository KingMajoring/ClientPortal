import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { NotificationsBell } from "../../shared/components/NotificationsBell";

export function StaffLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="portal-shell">
      <header className="portal-header">
        <h1>WGTK Staff Portal</h1>
        <nav>
          <NavLink to="/staff/enquiries">Enquiries</NavLink>
          <NavLink to="/staff/clients">Clients</NavLink>
          {user?.role === "WGTK_ADMIN" && <NavLink to="/staff/users">Users</NavLink>}
          <NavLink to="/staff/dashboard">Dashboard</NavLink>
        </nav>
        <div className="header-right">
          <NotificationsBell />
          <span>{user ? `${user.first_name} ${user.last_name}` : ""}</span>
          <button onClick={logout}>Log out</button>
        </div>
      </header>
      <main className="portal-main">
        <Outlet />
      </main>
      <footer className="powered-by">Powered by WGTK</footer>
    </div>
  );
}
