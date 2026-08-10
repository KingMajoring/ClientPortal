import { useEffect, useState } from "react";
import { api } from "../../shared/api/client";
import { Dashboard } from "../../shared/dashboard/Dashboard";

export function StaffDashboardPage() {
  const [clients, setClients] = useState([]);

  useEffect(() => {
    api.get("/staff/clients").then(setClients).catch(() => {});
  }, []);

  return (
    <div>
      <div className="page-header">
        <h2>SLA / MI dashboard</h2>
        <p className="subtitle">SLA compliance and job volume across all clients.</p>
      </div>
      <Dashboard clients={clients} canExport />
    </div>
  );
}
