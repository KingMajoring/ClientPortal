import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../shared/api/client";
import { Icon } from "../../shared/components/Icon";
import { StatusBadge } from "../../shared/components/StatusBadge";

export function ClientEnquiryListPage() {
  const [enquiries, setEnquiries] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.get("/client/enquiries").then(setEnquiries).catch((err) => setError(err.message));
  }, []);

  return (
    <div>
      <div className="page-header">
        <div className="page-header-row">
          <div>
            <h2>My enquiries</h2>
            <p className="subtitle">Enquiries raised by anyone at your company.</p>
          </div>
          <div className="page-header-actions">
            <Link className="button" to="/portal/enquiries/new">
              <Icon name="plus" size={16} />
              Raise enquiry
            </Link>
          </div>
        </div>
      </div>
      {error && <p className="form-error">{error}</p>}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Reference</th>
              <th>Vehicle</th>
              <th>Status</th>
              <th>ETA</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {enquiries.length === 0 && (
              <tr>
                <td colSpan={5} style={{ textAlign: "center", color: "var(--text-tertiary)", padding: "2rem" }}>
                  No enquiries yet — raise your first one above.
                </td>
              </tr>
            )}
            {enquiries.map((e) => (
              <tr key={e.id}>
                <td style={{ fontWeight: 600 }}>{e.reference}</td>
                <td>{e.vehicle_registration}</td>
                <td>
                  <StatusBadge status={e.status} />
                </td>
                <td>{e.eta_date || (e.scheduled_at ? new Date(e.scheduled_at).toLocaleString() : "-")}</td>
                <td>
                  <Link to={`/portal/enquiries/${e.id}`}>View</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
