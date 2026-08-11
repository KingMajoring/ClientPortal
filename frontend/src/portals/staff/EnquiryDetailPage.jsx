import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../../shared/api/client";
import { Icon } from "../../shared/components/Icon";
import { StatusBadge } from "../../shared/components/StatusBadge";

export function EnquiryDetailPage() {
  const { id } = useParams();
  const [enquiry, setEnquiry] = useState(null);
  const [notes, setNotes] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [error, setError] = useState(null);

  function reload() {
    api.get(`/staff/enquiries/${id}`).then(setEnquiry).catch((err) => setError(err.message));
    api.get(`/staff/enquiries/${id}/notes`).then(setNotes);
    api.get(`/staff/enquiries/${id}/documents`).then(setDocuments);
  }

  useEffect(reload, [id]);

  async function act(action, body) {
    setError(null);
    try {
      await api.post(`/staff/enquiries/${id}/${action}`, body);
      reload();
    } catch (err) {
      setError(err.message);
    }
  }

  if (!enquiry) return <p className="page-loading">{error || "Loading..."}</p>;

  return (
    <div>
      <div className="page-header">
        <Link to="/staff/enquiries" className="breadcrumb">
          <Icon name="chevronLeft" size={16} />
          Back to enquiries
        </Link>
        <div className="page-header-row">
          <div>
            <h2>
              {enquiry.reference} — {enquiry.client_company_name}
            </h2>
            <p className="subtitle">
              <StatusBadge status={enquiry.status} />
              {enquiry.is_eta_expired && <span className="badge badge-red" style={{ marginLeft: "0.5rem" }}>ETA expired</span>}
              {enquiry.external_ref?.startsWith("apex:") && (
                <span className="badge badge-gray" style={{ marginLeft: "0.5rem" }}>
                  Synced from Apex (job {enquiry.external_ref.replace("apex:", "")})
                </span>
              )}
            </p>
          </div>
        </div>
      </div>
      {error && <p className="form-error">{error}</p>}

      <CardSection icon="doc" title="Details">
        <dl className="detail-grid">
          <dt>Vehicle</dt>
          <dd>
            {enquiry.vehicle_registration} {enquiry.vehicle_make_model}
            {enquiry.vehicle_year && ` (${enquiry.vehicle_year})`}
          </dd>
          <dt>Location</dt>
          <dd>{enquiry.location_address}</dd>
          <dt>Urgency</dt>
          <dd>{enquiry.urgency}</dd>
        </dl>
      </CardSection>

      <ActionPanel enquiry={enquiry} act={act} />

      <CardSection icon="file" title="Job notes">
        <NoteForm onSubmit={(note_text, visibility) => act("notes", { note_text, visibility })} />
        <ul className="plain-list">
          {notes.map((n) => (
            <li key={n.id}>
              <span className={`badge ${n.visibility === "INTERNAL" ? "badge-gray" : "badge-blue"}`}>
                {n.visibility === "INTERNAL" ? "Internal" : "Client-visible"}
              </span>{" "}
              {n.note_text}
              <br />
              <small>{n.author_name} &middot; {new Date(n.created_at).toLocaleString()}</small>
            </li>
          ))}
        </ul>
      </CardSection>

      <CardSection icon="building" title="Documents">
        <DocumentUploadForm enquiryId={id} onUploaded={reload} />
        <ul className="plain-list">
          {documents.map((d) => (
            <li key={d.id}>
              <a href={d.download_url}>{d.original_filename}</a> ({d.document_type}, {d.visibility})
              {d.status && <span> &mdash; {d.status}</span>}
            </li>
          ))}
        </ul>
      </CardSection>

      <CardSection icon="chart" title="Status history">
        <ul className="plain-list">
          {enquiry.status_history.map((h) => (
            <li key={h.id}>
              {h.from_status || "—"} &rarr; {h.to_status} by {h.changed_by_name} at{" "}
              {new Date(h.created_at).toLocaleString()}
              {h.reason && <em> ({h.reason})</em>}
            </li>
          ))}
        </ul>
      </CardSection>
    </div>
  );
}

function CardSection({ icon, title, children }) {
  return (
    <section className="card">
      <div className="card-header">
        <div className="card-header-title">
          <div className="icon-badge">
            <Icon name={icon} size={16} />
          </div>
          <h3>{title}</h3>
        </div>
      </div>
      {children}
    </section>
  );
}

function ActionPanel({ enquiry, act }) {
  const [etaDate, setEtaDate] = useState("");
  const [etaSameDay, setEtaSameDay] = useState(false);
  const [price, setPrice] = useState("");
  const [scheduledAt, setScheduledAt] = useState("");
  const [rescheduleReason, setRescheduleReason] = useState("");
  const [declineReason, setDeclineReason] = useState("");
  const [completionNotes, setCompletionNotes] = useState("");

  const hasActions =
    ["NEW", "ETA_EXPIRED"].includes(enquiry.status) ||
    enquiry.status === "ACCEPTED" ||
    ["SCHEDULED", "ETA_EXPIRED"].includes(enquiry.status);

  if (!hasActions) return null;

  return (
    <CardSection icon="check" title="Actions">
      {(enquiry.status === "NEW" || enquiry.status === "ETA_EXPIRED") && (
        <div className="action-row">
          <h4 className="section-title">Send quote</h4>
          <input type="date" value={etaDate} onChange={(e) => setEtaDate(e.target.value)} />
          <label style={{ flexDirection: "row", alignItems: "center", gap: "0.4rem" }}>
            <input type="checkbox" checked={etaSameDay} onChange={(e) => setEtaSameDay(e.target.checked)} style={{ width: "auto" }} /> Same day
          </label>
          <input type="number" step="0.01" placeholder="Price" value={price} onChange={(e) => setPrice(e.target.value)} />
          <button onClick={() => act("quote", { eta_date: etaDate, eta_is_same_day: etaSameDay, price })}>
            Send quote
          </button>
          <input placeholder="Decline reason" value={declineReason} onChange={(e) => setDeclineReason(e.target.value)} />
          <button className="btn-danger" onClick={() => act("decline", { reason_text: declineReason })}>Decline</button>
        </div>
      )}

      {enquiry.status === "ACCEPTED" && (
        <div className="action-row">
          <h4 className="section-title">Set appointment time</h4>
          <input type="datetime-local" value={scheduledAt} onChange={(e) => setScheduledAt(e.target.value)} />
          <button onClick={() => act("schedule", { scheduled_at: scheduledAt })}>Send appointment time</button>
        </div>
      )}

      {(enquiry.status === "SCHEDULED" || enquiry.status === "ETA_EXPIRED") && (
        <div className="action-row">
          <h4 className="section-title">Reschedule</h4>
          <input type="datetime-local" value={scheduledAt} onChange={(e) => setScheduledAt(e.target.value)} />
          <input placeholder="Reason (required)" value={rescheduleReason} onChange={(e) => setRescheduleReason(e.target.value)} />
          <button onClick={() => act("reschedule", { scheduled_at: scheduledAt, reason: rescheduleReason })}>
            Reschedule
          </button>
        </div>
      )}

      {(enquiry.status === "SCHEDULED" || enquiry.status === "ETA_EXPIRED") && (
        <div className="action-row">
          <h4 className="section-title">Mark complete</h4>
          <textarea
            placeholder="Completion notes"
            value={completionNotes}
            onChange={(e) => setCompletionNotes(e.target.value)}
          />
          <button onClick={() => act("complete", { completion_notes: completionNotes })}>Mark complete</button>
        </div>
      )}
    </CardSection>
  );
}

function NoteForm({ onSubmit }) {
  const [text, setText] = useState("");
  const [visibility, setVisibility] = useState("INTERNAL");

  return (
    <div className="note-form">
      <textarea placeholder="Add a note" value={text} onChange={(e) => setText(e.target.value)} />
      <select value={visibility} onChange={(e) => setVisibility(e.target.value)}>
        <option value="INTERNAL">Internal only</option>
        <option value="CLIENT_VISIBLE">Client-visible</option>
      </select>
      <button
        onClick={() => {
          onSubmit(text, visibility);
          setText("");
        }}
      >
        Add note
      </button>
    </div>
  );
}

function DocumentUploadForm({ enquiryId, onUploaded }) {
  const [file, setFile] = useState(null);
  const [documentType, setDocumentType] = useState("JOB_SHEET");
  const [visibility, setVisibility] = useState("CLIENT_VISIBLE");

  async function upload() {
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    form.append("document_type", documentType);
    form.append("visibility", visibility);
    await api.post(`/staff/enquiries/${enquiryId}/documents`, form);
    setFile(null);
    onUploaded();
  }

  return (
    <div className="document-upload-form">
      <input type="file" onChange={(e) => setFile(e.target.files[0])} />
      <select value={documentType} onChange={(e) => setDocumentType(e.target.value)}>
        <option value="JOB_SHEET">Job sheet</option>
        <option value="COMPLETION_REPORT">Completion report</option>
        <option value="OTHER">Other</option>
      </select>
      <select value={visibility} onChange={(e) => setVisibility(e.target.value)}>
        <option value="CLIENT_VISIBLE">Client-visible</option>
        <option value="INTERNAL">Internal only</option>
      </select>
      <button onClick={upload}>Upload</button>
    </div>
  );
}
