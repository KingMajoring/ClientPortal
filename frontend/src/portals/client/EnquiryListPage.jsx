import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../shared/api/client";

export function ClientEnquiryListPage() {
  const [enquiries, setEnquiries] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.get("/client/enquiries").then(setEnquiries).catch((err) => setError(err.message));
  }, []);

  return (
    <div>
      <h2>My enquiries</h2>
      {error && <p className="form-error">{error}</p>}
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
          {enquiries.map((e) => (
            <tr key={e.id}>
              <td>{e.reference}</td>
              <td>{e.vehicle_registration}</td>
              <td>{e.status.replace(/_/g, " ")}</td>
              <td>{e.eta_date || (e.scheduled_at ? new Date(e.scheduled_at).toLocaleString() : "-")}</td>
              <td>
                <Link to={`/portal/enquiries/${e.id}`}>View</Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
