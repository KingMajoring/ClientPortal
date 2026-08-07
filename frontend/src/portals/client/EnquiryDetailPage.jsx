import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../../shared/api/client";

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

  if (!enquiry) return <p>{error || "Loading..."}</p>;

  const loaDoc = documents.find((d) => d.document_type === "LETTER_OF_AUTHORITY");

  return (
    <div className="enquiry-detail">
      <h2>{enquiry.reference}</h2>
      <p>
        Status: <strong>{enquiry.status.replace(/_/g, " ")}</strong>
      </p>
      {error && <p className="form-error">{error}</p>}

      <section>
        <dl>
          <dt>Vehicle</dt>
          <dd>{enquiry.vehicle_registration} {enquiry.vehicle_make_model}</dd>
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
        <section className="action-panel">
          <h3>Respond to quote</h3>
          <button onClick={accept}>Accept quote</button>
          <div className="action-row">
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
            <button onClick={decline}>Decline quote</button>
          </div>
        </section>
      )}

      {loaDoc && (
        <section>
          <h3>Letter of Authority</h3>
          <p>
            <a href={loaDoc.download_url}>{loaDoc.original_filename}</a> &mdash; {loaDoc.status}
          </p>
          {loaDoc.status === "PENDING_ACCEPTANCE" && (
            <button onClick={() => acceptLoa(loaDoc.id)}>Digitally accept Letter of Authority</button>
          )}
        </section>
      )}

      {enquiry.status === "ACCEPTED" && (
        <section>
          <h3>Upload required documents</h3>
          <DocumentUploadForm enquiryId={id} onUploaded={reload} />
        </section>
      )}

      <section>
        <h3>Documents</h3>
        <ul>
          {documents.map((d) => (
            <li key={d.id}>
              <a href={d.download_url}>{d.original_filename}</a> ({d.document_type})
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h3>Job notes</h3>
        <ul>
          {notes.map((n) => (
            <li key={n.id}>
              {n.note_text}
              <br />
              <small>{new Date(n.created_at).toLocaleString()}</small>
            </li>
          ))}
        </ul>
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
