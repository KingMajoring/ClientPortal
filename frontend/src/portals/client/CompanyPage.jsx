import { useEffect, useState } from "react";
import { api } from "../../shared/api/client";
import { Icon } from "../../shared/components/Icon";

export function CompanyPage() {
  const [users, setUsers] = useState([]);
  const [flags, setFlags] = useState({});
  const [form, setForm] = useState({ email: "", first_name: "", last_name: "", role: "CLIENT_GENERAL" });
  const [tempPassword, setTempPassword] = useState(null);
  const [error, setError] = useState(null);

  function reload() {
    api.get("/client/users").then(setUsers).catch((err) => setError(err.message));
    api.get("/client/feature-flags").then(setFlags);
  }

  useEffect(reload, []);

  function set(field) {
    return (e) => setForm({ ...form, [field]: e.target.value });
  }

  async function submit(e) {
    e.preventDefault();
    setError(null);
    try {
      const res = await api.post("/client/users", form);
      setTempPassword(res.temp_password);
      reload();
    } catch (err) {
      setError(err.message);
    }
  }

  async function toggleFlag(key) {
    const updated = await api.put("/client/feature-flags", { flags: { [key]: !flags[key] } });
    setFlags(updated);
  }

  async function resetPassword(userId) {
    const res = await api.post(`/client/users/${userId}/reset-password`, {});
    setTempPassword(res.temp_password);
  }

  async function removeUser(userId) {
    await api.del(`/client/users/${userId}`);
    reload();
  }

  return (
    <div>
      <div className="page-header">
        <h2>Company settings</h2>
        <p className="subtitle">Manage your team and what standard users can see.</p>
      </div>

      <section className="card">
        <div className="card-header">
          <div className="card-header-title">
            <div className="icon-badge">
              <Icon name="settings" size={16} />
            </div>
            <h3>Feature visibility for standard users</h3>
          </div>
        </div>
        <div className="action-row">
          {Object.entries(flags).map(([key, enabled]) => (
            <label key={key} className={`toggle-chip ${enabled ? "checked" : ""}`}>
              <input type="checkbox" checked={enabled} onChange={() => toggleFlag(key)} />
              <Icon name={enabled ? "check" : "x"} size={14} />
              {key.replace(/_/g, " ")}
            </label>
          ))}
        </div>
      </section>

      <section className="card">
        <div className="card-header">
          <div className="card-header-title">
            <div className="icon-badge">
              <Icon name="users" size={16} />
            </div>
            <h3>Users</h3>
          </div>
        </div>
        <form onSubmit={submit} className="onboard-form">
          <input placeholder="Email" type="email" value={form.email} onChange={set("email")} required />
          <input placeholder="First name" value={form.first_name} onChange={set("first_name")} required />
          <input placeholder="Last name" value={form.last_name} onChange={set("last_name")} required />
          <select value={form.role} onChange={set("role")}>
            <option value="CLIENT_GENERAL">Standard user</option>
            <option value="CLIENT_ADMIN">Admin</option>
          </select>
          <button type="submit">Add user</button>
        </form>
        {error && <p className="form-error">{error}</p>}
        {tempPassword && <p className="form-success">Temp password: <code>{tempPassword}</code></p>}
      </section>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td style={{ fontWeight: 600 }}>{u.first_name} {u.last_name}</td>
                <td>{u.email}</td>
                <td><span className={`badge ${u.role === "CLIENT_ADMIN" ? "badge-blue" : "badge-gray"}`}>{u.role === "CLIENT_ADMIN" ? "Admin" : "Standard"}</span></td>
                <td className="action-row" style={{ margin: 0 }}>
                  <button className="btn-secondary" onClick={() => resetPassword(u.id)}>Reset password</button>
                  <button className="btn-danger" onClick={() => removeUser(u.id)}>Remove</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
