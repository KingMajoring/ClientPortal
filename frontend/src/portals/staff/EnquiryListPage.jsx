import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../shared/api/client";
import { Icon } from "../../shared/components/Icon";
import { StatusBadge } from "../../shared/components/StatusBadge";

export function EnquiryListPage() {
  const [enquiries, setEnquiries] = useState([]);
  const [status, setStatus] = useState("");
  const [error, setError] = useState(null);

  function load() {
    const params = status ? `?status=${status}` : "";
    api
      .get(`/staff/enquiries${params}`)
      .then(setEnquiries)
      .catch((err) => setError(err.message));
  }

  useEffect(load, [status]);

  return (
    <div>
      <div className="page-header">
        <div className="page-header-row">
          <div>
            <h2>Enquiry inbox</h2>
            <p className="subtitle">All enquiries across every client, newest first.</p>
          </div>
        </div>
      </div>

      <div className="list-filters">
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          {["NEW", "QUOTED", "ACCEPTED", "SCHEDULED", "ETA_EXPIRED", "DECLINED_BY_CLIENT", "DECLINED_BY_WGTK", "COMPLETED"].map(
            (s) => (
              <option key={s} value={s}>
                {s.replace(/_/g, " ")}
              </option>
            )
          )}
        </select>
      </div>
      {error && <p className="form-error">{error}</p>}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Reference</th>
              <th>Client</th>
              <th>Vehicle</th>
              <th>Status</th>
              <th>ETA expired?</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {enquiries.length === 0 && (
              <tr>
                <td colSpan={6} style={{ textAlign: "center", color: "var(--text-tertiary)", padding: "2rem" }}>
                  No enquiries yet.
                </td>
              </tr>
            )}
            {enquiries.map((e) => (
              <tr key={e.id} className={e.is_eta_expired ? "row-alert" : ""}>
                <td style={{ fontWeight: 600 }}>{e.reference}</td>
                <td>{e.client_company_name}</td>
                <td>{e.vehicle_registration}</td>
                <td>
                  <StatusBadge status={e.status} />
                </td>
                <td>{e.is_eta_expired && <Icon name="alert" size={16} style={{ color: "var(--danger)" }} />}</td>
                <td>
                  <Link to={`/staff/enquiries/${e.id}`}>View</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
