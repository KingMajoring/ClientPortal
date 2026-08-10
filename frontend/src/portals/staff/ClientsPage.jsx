import { useEffect, useState } from "react";
import { api } from "../../shared/api/client";
import { Icon } from "../../shared/components/Icon";

export function ClientsPage() {
  const [clients, setClients] = useState([]);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState(null);

  function reload() {
    api.get("/staff/clients").then(setClients).catch((err) => setError(err.message));
  }

  useEffect(reload, []);

  return (
    <div>
      <div className="page-header">
        <h2>Client companies</h2>
        <p className="subtitle">Onboard trade clients and configure their SLA targets and service types.</p>
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
                  <button className="btn-secondary" onClick={() => setSelected(c)}>Configure</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && <ClientConfigPanel client={selected} onSaved={() => { reload(); setSelected(null); }} />}
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
    </section>
  );
}

function ClientConfigPanel({ client, onSaved }) {
  const [targets, setTargets] = useState(client.sla_targets);
  const [serviceTypeNames, setServiceTypeNames] = useState(client.service_types.map((s) => s.name).join(", "));

  async function saveTargets() {
    await api.put(`/staff/clients/${client.id}/sla-targets`, { targets });
    onSaved();
  }

  async function saveServiceTypes() {
    const names = serviceTypeNames.split(",").map((n) => n.trim()).filter(Boolean);
    await api.put(`/staff/clients/${client.id}/service-types`, { names });
    onSaved();
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
      </div>

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
    </section>
  );
}
