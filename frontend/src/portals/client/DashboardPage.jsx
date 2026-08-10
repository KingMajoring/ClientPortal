import { Dashboard } from "../../shared/dashboard/Dashboard";

export function ClientDashboardPage() {
  return (
    <div>
      <div className="page-header">
        <h2>SLA / MI dashboard</h2>
        <p className="subtitle">Your company's SLA performance and job volume.</p>
      </div>
      <Dashboard />
    </div>
  );
}
