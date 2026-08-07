import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { NotificationsBell } from "../../shared/components/NotificationsBell";

export function ClientLayout() {
  const { user, logout } = useAuth();
  const [branding, setBranding] = useState(null);

  useEffect(() => {
    if (user?.client_company) setBranding(user.client_company);
  }, [user]);

  const style = branding?.primary_color ? { "--brand-color": branding.primary_color } : {};

  return (
    <div className="portal-shell" style={style}>
      <header className="portal-header branded">
        {branding?.logo_path && <img className="brand-logo" src={branding.logo_path} alt={branding.name} />}
        <h1>{branding?.name || "Client Portal"}</h1>
        <nav>
          <NavLink to="/portal/enquiries/new">Raise enquiry</NavLink>
          <NavLink to="/portal/enquiries">My enquiries</NavLink>
          <NavLink to="/portal/dashboard">Dashboard</NavLink>
          {user?.role === "CLIENT_ADMIN" && <NavLink to="/portal/company">Company</NavLink>}
        </nav>
        <div className="header-right">
          <NotificationsBell />
          <span>{user?.first_name} {user?.last_name}</span>
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
