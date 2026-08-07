import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../shared/api/client";

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
      <h2>Enquiry inbox</h2>
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
          {enquiries.map((e) => (
            <tr key={e.id} className={e.is_eta_expired ? "row-alert" : ""}>
              <td>{e.reference}</td>
              <td>{e.client_company_name}</td>
              <td>{e.vehicle_registration}</td>
              <td>{e.status.replace(/_/g, " ")}</td>
              <td>{e.is_eta_expired ? "Yes" : ""}</td>
              <td>
                <Link to={`/staff/enquiries/${e.id}`}>View</Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
