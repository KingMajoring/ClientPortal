import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Icon } from "../components/Icon";

const METRIC_LABELS = {
  time_to_quote: "Time to quote",
  time_to_attend: "Time to attend",
  time_to_complete: "Time to complete",
};

/**
 * Shared SLA/MI dashboard. WGTK's staff portal passes `clients` (the list to
 * filter by) and `canExport`; the client portal renders the same component
 * with neither, scoped server-side to the caller's own company.
 */
export function Dashboard({ clients, canExport }) {
  const [clientCompanyId, setClientCompanyId] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const params = new URLSearchParams();
    if (clientCompanyId) params.set("client_company_id", clientCompanyId);
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    api
      .get(`/shared/dashboard?${params.toString()}`)
      .then(setData)
      .catch((err) => setError(err.message));
  }, [clientCompanyId, dateFrom, dateTo]);

  return (
    <div className="dashboard">
      <div className="list-filters">
        {clients && (
          <select value={clientCompanyId} onChange={(e) => setClientCompanyId(e.target.value)}>
            <option value="">All clients</option>
            {clients.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        )}
        <label style={{ flexDirection: "row", alignItems: "center", gap: "0.4rem" }}>
          From <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        </label>
        <label style={{ flexDirection: "row", alignItems: "center", gap: "0.4rem" }}>
          To <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        </label>
        {canExport && (
          <a
            className="button btn-secondary"
            href={`/api/staff/enquiries/export.csv${clientCompanyId ? `?client_company_id=${clientCompanyId}` : ""}`}
          >
            <Icon name="file" size={16} />
            Export CSV
          </a>
        )}
      </div>

      {error && <p className="form-error">{error}</p>}
      {!data && !error && <p className="page-loading">Loading dashboard...</p>}

      {data && (
        <>
          <div className="stat-row" style={{ marginBottom: "1.25rem" }}>
            <div className="stat-tile">
              <div className="stat-value">{data.mi.total}</div>
              <div className="stat-label">Total enquiries</div>
            </div>
            <div className="stat-tile">
              <div className="stat-value" style={{ color: data.mi.eta_expired_count > 0 ? "var(--danger)" : undefined }}>
                {data.mi.eta_expired_count}
              </div>
              <div className="stat-label">ETA expired</div>
            </div>
            {Object.entries(data.mi.counts_by_status).map(([status, count]) => (
              <div className="stat-tile" key={status}>
                <div className="stat-value">{count}</div>
                <div className="stat-label">{status.replace(/_/g, " ")}</div>
              </div>
            ))}
          </div>

          <section className="card">
            <div className="card-header">
              <div className="card-header-title">
                <div className="icon-badge">
                  <Icon name="chart" size={16} />
                </div>
                <h3>SLA compliance</h3>
              </div>
            </div>
            <div className="table-wrap" style={{ boxShadow: "none", marginBottom: 0 }}>
              <table>
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th>Target (hrs)</th>
                    <th>Average (hrs)</th>
                    <th>Sample</th>
                    <th>Breaches</th>
                    <th>Compliance</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(data.sla_compliance).map(([key, row]) => (
                    <tr key={key}>
                      <td style={{ fontWeight: 600 }}>{METRIC_LABELS[key] || key}</td>
                      <td>{row.target_hours ?? "-"}</td>
                      <td>{row.average_hours ?? "-"}</td>
                      <td>{row.sample_size}</td>
                      <td>{row.breaches}</td>
                      <td>{row.compliance_rate != null ? `${Math.round(row.compliance_rate * 100)}%` : "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="card">
            <div className="card-header">
              <div className="card-header-title">
                <div className="icon-badge">
                  <Icon name="inbox" size={16} />
                </div>
                <h3>Volume over time</h3>
              </div>
            </div>
            <ul className="volume-list">
              {Object.entries(data.mi.volume_by_day).map(([day, count]) => (
                <li key={day}>
                  {day}: <strong>{count}</strong>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </div>
  );
}
