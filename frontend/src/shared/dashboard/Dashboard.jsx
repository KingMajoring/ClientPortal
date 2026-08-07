import { useEffect, useState } from "react";
import { api } from "../api/client";

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
      <div className="dashboard-filters">
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
        <label>
          From <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        </label>
        <label>
          To <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        </label>
        {canExport && (
          <a
            className="button"
            href={`/api/staff/enquiries/export.csv${clientCompanyId ? `?client_company_id=${clientCompanyId}` : ""}`}
          >
            Export CSV
          </a>
        )}
      </div>

      {error && <p className="form-error">{error}</p>}
      {!data && !error && <p>Loading dashboard...</p>}

      {data && (
        <>
          <section>
            <h3>SLA compliance</h3>
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
                    <td>{METRIC_LABELS[key] || key}</td>
                    <td>{row.target_hours ?? "-"}</td>
                    <td>{row.average_hours ?? "-"}</td>
                    <td>{row.sample_size}</td>
                    <td>{row.breaches}</td>
                    <td>{row.compliance_rate != null ? `${Math.round(row.compliance_rate * 100)}%` : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section>
            <h3>Job counts by status</h3>
            <ul className="status-counts">
              {Object.entries(data.mi.counts_by_status).map(([status, count]) => (
                <li key={status}>
                  <strong>{count}</strong> {status.replace(/_/g, " ")}
                </li>
              ))}
            </ul>
            <p>
              Total: {data.mi.total} &middot; ETA expired: {data.mi.eta_expired_count}
            </p>
          </section>

          <section>
            <h3>Volume over time</h3>
            <ul className="volume-list">
              {Object.entries(data.mi.volume_by_day).map(([day, count]) => (
                <li key={day}>
                  {day}: {count}
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </div>
  );
}
