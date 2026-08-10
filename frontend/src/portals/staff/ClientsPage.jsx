import { useEffect, useState } from "react";
import { api } from "../../shared/api/client";
import { Icon } from "../../shared/components/Icon";

const STANDARD_FIELDS = [
  { field_key: "vehicle_registration", label: "Vehicle Registration", field_type: "text" },
  { field_key: "vehicle_make_model", label: "Make / Model", field_type: "text" },
  { field_key: "location_address", label: "Site Address", field_type: "textarea" },
  { field_key: "urgency", label: "Urgency", field_type: "select", options: ["Standard", "Urgent", "Same Day"] },
  { field_key: "on_site_contact_name", label: "On-site Contact", field_type: "text" },
  { field_key: "on_site_contact_phone", label: "On-site Contact Phone", field_type: "text" },
];

export function ClientsPage() {
  const [clients, setClients] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [error, setError] = useState(null);

  function reload() {
    return api.get("/staff/clients").then(setClients).catch((err) => setError(err.message));
  }

  useEffect(() => {
    reload();
  }, []);

  const selected = clients.find((c) => c.id === selectedId);

  return (
    <div>
      <div className="page-header">
        <h2>Client companies</h2>
        <p className="subtitle">Onboard trade clients and configure their SLA targets, service types, and enquiry form.</p>
      </div>
      {error && <p className="form-error">{error}</p>}
      <OnboardClientForm onOnboarded={reload} />

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Colour</th>
              <th>SLA targets</th>
              <th>Service types</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {clients.map((c) => (
              <tr key={c.id}>
                <td style={{ fontWeight: 600 }}>{c.name}</td>
                <td>
                  <span className="color-swatch" style={{ background: c.primary_color }} /> {c.primary_color}
                </td>
                <td>{Object.entries(c.sla_targets).map(([k, v]) => `${k}: ${v}h`).join(", ") || "Not set"}</td>
                <td>{c.service_types.map((s) => s.name).join(", ") || "None"}</td>
                <td>
                  <button className="btn-secondary" onClick={() => setSelectedId(c.id)}>Configure</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && <ClientConfigPanel client={selected} onSaved={reload} onClose={() => setSelectedId(null)} />}
    </div>
  );
}

function OnboardClientForm({ onOnboarded }) {
  const [form, setForm] = useState({ name: "", primary_color: "#0B5FFF", admin_email: "", admin_first_name: "", admin_last_name: "" });
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  function set(field) {
    return (e) => setForm({ ...form, [field]: e.target.value });
  }

  async function submit(e) {
    e.preventDefault();
    setError(null);
    try {
      const res = await api.post("/staff/clients", form);
      setResult(res);
      onOnboarded();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="card">
      <div className="card-header">
        <div className="card-header-title">
          <div className="icon-badge">
            <Icon name="plus" size={16} />
          </div>
          <h3>Onboard a new client</h3>
        </div>
      </div>
      <form className="onboard-form" onSubmit={submit}>
        <input placeholder="Company name" value={form.name} onChange={set("name")} required />
        <input type="color" value={form.primary_color} onChange={set("primary_color")} style={{ width: 44, padding: 2 }} />
        <input placeholder="Admin email" type="email" value={form.admin_email} onChange={set("admin_email")} required />
        <input placeholder="Admin first name" value={form.admin_first_name} onChange={set("admin_first_name")} required />
        <input placeholder="Admin last name" value={form.admin_last_name} onChange={set("admin_last_name")} required />
        <button type="submit">Onboard client</button>
      </form>
      {error && <p className="form-error">{error}</p>}
      {result && (
        <p className="form-success">
          Created {result.client_company.name}. Temp password for {result.admin_user.email}: <code>{result.temp_password}</code>
        </p>
      )}
      <p style={{ color: "var(--text-tertiary)", fontSize: "0.8rem", marginTop: "0.5rem" }}>
        A new client has no enquiry form fields yet — click "Configure" below to add them, or their Raise Enquiry
        page will have nothing to fill in.
      </p>
    </section>
  );
}

function ClientConfigPanel({ client, onSaved, onClose }) {
  const [targets, setTargets] = useState(client.sla_targets);
  const [serviceTypeNames, setServiceTypeNames] = useState(client.service_types.map((s) => s.name).join(", "));
  const [fields, setFields] = useState(client.form_fields.map(toEditableField));
  const [savedMessage, setSavedMessage] = useState(null);
  const [error, setError] = useState(null);

  function toEditableField(f) {
    return {
      field_key: f.field_key,
      label: f.label,
      field_type: f.field_type,
      is_required: f.is_required,
      optionsText: (f.options || []).join(", "),
    };
  }

  async function saveTargets() {
    setError(null);
    try {
      await onSavedWrap(api.put(`/staff/clients/${client.id}/sla-targets`, { targets }));
      setSavedMessage("SLA targets saved.");
    } catch (err) {
      setError(err.message);
    }
  }

  async function saveServiceTypes() {
    setError(null);
    const names = serviceTypeNames.split(",").map((n) => n.trim()).filter(Boolean);
    try {
      await onSavedWrap(api.put(`/staff/clients/${client.id}/service-types`, { names }));
      setSavedMessage("Service types saved.");
    } catch (err) {
      setError(err.message);
    }
  }

  async function saveFields() {
    setError(null);
    const payload = fields.map((f, i) => ({
      field_key: f.field_key,
      label: f.label,
      field_type: f.field_type,
      is_required: f.is_required,
      options: f.field_type === "select" ? f.optionsText.split(",").map((o) => o.trim()).filter(Boolean) : undefined,
      sort_order: i,
    }));
    try {
      await onSavedWrap(api.put(`/staff/clients/${client.id}/form-fields`, { fields: payload }));
      setSavedMessage("Enquiry form fields saved.");
    } catch (err) {
      setError(err.message);
    }
  }

  async function onSavedWrap(promise) {
    await promise;
    await onSaved();
  }

  function updateField(index, patch) {
    setFields((prev) => prev.map((f, i) => (i === index ? { ...f, ...patch } : f)));
  }

  function removeField(index) {
    setFields((prev) => prev.filter((_, i) => i !== index));
  }

  function addField(preset) {
    if (preset && fields.some((f) => f.field_key === preset.field_key)) return;
    setFields((prev) => [
      ...prev,
      preset
        ? { ...preset, is_required: true, optionsText: (preset.options || []).join(", ") }
        : { field_key: "", label: "", field_type: "text", is_required: false, optionsText: "" },
    ]);
  }

  return (
    <section className="card">
      <div className="card-header">
        <div className="card-header-title">
          <div className="icon-badge">
            <Icon name="settings" size={16} />
          </div>
          <h3>Configure {client.name}</h3>
        </div>
        <button className="btn-ghost" onClick={onClose}>
          <Icon name="x" size={16} />
        </button>
      </div>
      {error && <p className="form-error">{error}</p>}
      {savedMessage && <p className="form-success">{savedMessage}</p>}

      <h4 className="section-title">SLA targets (hours)</h4>
      <div className="action-row">
        {["time_to_quote", "time_to_attend", "time_to_complete"].map((key) => (
          <label key={key} style={{ minWidth: 160 }}>
            {key.replace(/_/g, " ")}
            <input
              type="number"
              value={targets[key] || ""}
              onChange={(e) => setTargets({ ...targets, [key]: parseFloat(e.target.value) })}
            />
          </label>
        ))}
      </div>
      <button onClick={saveTargets}>Save SLA targets</button>

      <h4 className="section-title" style={{ marginTop: "1.5rem" }}>Service types (comma-separated)</h4>
      <div className="action-row">
        <input style={{ flex: 1 }} value={serviceTypeNames} onChange={(e) => setServiceTypeNames(e.target.value)} />
        <button onClick={saveServiceTypes}>Save service types</button>
      </div>

      <h4 className="section-title" style={{ marginTop: "1.5rem" }}>Enquiry form fields</h4>
      <p style={{ color: "var(--text-secondary)", fontSize: "0.82rem", marginTop: "-0.5rem" }}>
        What this client's users see and must fill in on "Raise enquiry."
      </p>

      {fields.length === 0 && (
        <p style={{ color: "var(--text-tertiary)", fontSize: "0.85rem" }}>
          No fields configured yet — this client's Raise Enquiry page is currently empty.
        </p>
      )}

      {fields.map((f, i) => (
        <div className="action-row" key={i} style={{ background: "#FAFAFC", padding: "0.6rem", borderRadius: "var(--radius-sm)" }}>
          <input
            placeholder="field_key"
            value={f.field_key}
            onChange={(e) => updateField(i, { field_key: e.target.value.trim().replace(/\s+/g, "_") })}
            style={{ width: 170 }}
          />
          <input
            placeholder="Label shown to client"
            value={f.label}
            onChange={(e) => updateField(i, { label: e.target.value })}
            style={{ flex: 1, minWidth: 160 }}
          />
          <select value={f.field_type} onChange={(e) => updateField(i, { field_type: e.target.value })}>
            <option value="text">Text</option>
            <option value="textarea">Text area</option>
            <option value="select">Dropdown</option>
            <option value="date">Date</option>
            <option value="checkbox">Checkbox</option>
          </select>
          {f.field_type === "select" && (
            <input
              placeholder="Options (comma-separated)"
              value={f.optionsText}
              onChange={(e) => updateField(i, { optionsText: e.target.value })}
              style={{ minWidth: 180 }}
            />
          )}
          <label style={{ flexDirection: "row", alignItems: "center", gap: "0.35rem" }}>
            <input type="checkbox" checked={f.is_required} onChange={(e) => updateField(i, { is_required: e.target.checked })} style={{ width: "auto" }} />
            Required
          </label>
          <button className="btn-danger" onClick={() => removeField(i)}>
            <Icon name="x" size={14} />
          </button>
        </div>
      ))}

      <div className="action-row">
        <button className="btn-secondary" onClick={() => addField(null)}>
          <Icon name="plus" size={14} />
          Custom field
        </button>
        {STANDARD_FIELDS.filter((s) => !fields.some((f) => f.field_key === s.field_key)).map((s) => (
          <button key={s.field_key} className="btn-secondary" onClick={() => addField(s)}>
            <Icon name="plus" size={14} />
            {s.label}
          </button>
        ))}
      </div>

      <button onClick={saveFields} style={{ marginTop: "0.75rem" }}>Save form fields</button>
    </section>
  );
}
