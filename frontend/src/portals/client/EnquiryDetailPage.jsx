import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../../shared/api/client";
import { Icon } from "../../shared/components/Icon";
import { StatusBadge } from "../../shared/components/StatusBadge";

export function ClientEnquiryDetailPage() {
  const { id } = useParams();
  const [enquiry, setEnquiry] = useState(null);
  const [notes, setNotes] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [error, setError] = useState(null);
  const [declineReasonType, setDeclineReasonType] = useState("PRICE");
  const [declineReasonText, setDeclineReasonText] = useState("");

  function reload() {
    api.get(`/client/enquiries/${id}`).then(setEnquiry).catch((err) => setError(err.message));
    api.get(`/client/enquiries/${id}/notes`).then(setNotes);
    api.get(`/client/enquiries/${id}/documents`).then(setDocuments);
  }

  useEffect(reload, [id]);

  async function accept() {
    setError(null);
    try {
      await api.post(`/client/enquiries/${id}/accept`, {});
      reload();
    } catch (err) {
      setError(err.message);
    }
  }

  async function decline() {
    setError(null);
    try {
      await api.post(`/client/enquiries/${id}/decline`, {
        reason_type: declineReasonType,
        reason_text: declineReasonText,
      });
      reload();
    } catch (err) {
      setError(err.message);
    }
  }

  async function acceptLoa(documentId) {
    await api.post(`/client/documents/${documentId}/accept-letter-of-authority`, {});
    reload();
  }

  if (!enquiry) return <p className="page-loading">{error || "Loading..."}</p>;

  const loaDoc = documents.find((d) => d.document_type === "LETTER_OF_AUTHORITY");

  return (
    <div>
      <div className="page-header">
        <Link to="/portal/enquiries" className="breadcrumb">
          <Icon name="chevronLeft" size={16} />
          Back to my enquiries
        </Link>
        <div className="page-header-row">
          <div>
            <h2>{enquiry.reference}</h2>
            <p className="subtitle">
              <StatusBadge status={enquiry.status} />
            </p>
          </div>
        </div>
      </div>
      {error && <p className="form-error">{error}</p>}

      <section className="card">
        <div className="card-header">
          <div className="card-header-title">
            <div className="icon-badge">
              <Icon name="doc" size={16} />
            </div>
            <h3>Details</h3>
          </div>
        </div>
        <dl className="detail-grid">
          <dt>Vehicle</dt>
          <dd>
            {enquiry.vehicle_registration} {enquiry.vehicle_make_model}
            {enquiry.vehicle_year && ` (${enquiry.vehicle_year})`}
          </dd>
          <dt>Location</dt>
          <dd>{enquiry.location_address}</dd>
          {enquiry.eta_date && (
            <>
              <dt>ETA</dt>
              <dd>{enquiry.eta_date} {enquiry.eta_is_same_day && "(same day)"}</dd>
            </>
          )}
          {enquiry.price && (
            <>
              <dt>Price</dt>
              <dd>£{enquiry.price}</dd>
            </>
          )}
          {enquiry.scheduled_at && (
            <>
              <dt>Appointment</dt>
              <dd>{new Date(enquiry.scheduled_at).toLocaleString()}</dd>
            </>
          )}
        </dl>
      </section>

      {enquiry.status === "QUOTED" && (
        <section className="card">
          <div className="card-header">
            <div className="card-header-title">
              <div className="icon-badge">
                <Icon name="check" size={16} />
              </div>
              <h3>Respond to quote</h3>
            </div>
          </div>
          <button onClick={accept}>Accept quote</button>
          <div className="action-row" style={{ marginTop: "1rem" }}>
            <select value={declineReasonType} onChange={(e) => setDeclineReasonType(e.target.value)}>
              <option value="PRICE">Decline: Price</option>
              <option value="ETA">Decline: ETA</option>
              <option value="OTHER">Decline: Other</option>
            </select>
            <input
              placeholder="Reason"
              value={declineReasonText}
              onChange={(e) => setDeclineReasonText(e.target.value)}
            />
            <button className="btn-danger" onClick={decline}>Decline quote</button>
          </div>
        </section>
      )}

      {loaDoc && (
        <section className="card">
          <div className="card-header">
            <div className="card-header-title">
              <div className="icon-badge">
                <Icon name="file" size={16} />
              </div>
              <h3>Letter of Authority</h3>
            </div>
            <span className={`badge ${loaDoc.status === "ACCEPTED" ? "badge-green" : "badge-amber"}`}>
              {loaDoc.status === "ACCEPTED" ? "Accepted" : "Pending acceptance"}
            </span>
          </div>
          <p>
            <a href={loaDoc.download_url}>{loaDoc.original_filename}</a>
          </p>
          {loaDoc.status === "PENDING_ACCEPTANCE" && (
            <button onClick={() => acceptLoa(loaDoc.id)}>Digitally accept Letter of Authority</button>
          )}
        </section>
      )}

      {enquiry.status === "ACCEPTED" && (
        <section className="card">
          <div className="card-header">
            <div className="card-header-title">
              <div className="icon-badge">
                <Icon name="plus" size={16} />
              </div>
              <h3>Upload required documents</h3>
            </div>
          </div>
          <DocumentUploadForm enquiryId={id} onUploaded={reload} />
        </section>
      )}

      <section className="card">
        <div className="card-header">
          <div className="card-header-title">
            <div className="icon-badge">
              <Icon name="building" size={16} />
            </div>
            <h3>Documents</h3>
          </div>
        </div>
        {documents.length === 0 ? (
          <p style={{ color: "var(--text-tertiary)" }}>No documents yet.</p>
        ) : (
          <ul className="plain-list">
            {documents.map((d) => (
              <li key={d.id}>
                <a href={d.download_url}>{d.original_filename}</a> ({d.document_type})
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card">
        <div className="card-header">
          <div className="card-header-title">
            <div className="icon-badge">
              <Icon name="inbox" size={16} />
            </div>
            <h3>Job notes</h3>
          </div>
        </div>
        {notes.length === 0 ? (
          <p style={{ color: "var(--text-tertiary)" }}>No notes yet.</p>
        ) : (
          <ul className="plain-list">
            {notes.map((n) => (
              <li key={n.id}>
                {n.note_text}
                <br />
                <small>{new Date(n.created_at).toLocaleString()}</small>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function DocumentUploadForm({ enquiryId, onUploaded }) {
  const [file, setFile] = useState(null);

  async function upload() {
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    form.append("document_type", "V5");
    await api.post(`/client/enquiries/${enquiryId}/documents`, form);
    setFile(null);
    onUploaded();
  }

  return (
    <div className="document-upload-form">
      <input type="file" onChange={(e) => setFile(e.target.files[0])} />
      <button onClick={upload}>Upload V5</button>
    </div>
  );
}
