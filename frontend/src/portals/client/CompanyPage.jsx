import { useEffect, useState } from "react";
import { api } from "../../shared/api/client";

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
      <h2>Company settings</h2>

      <section>
        <h3>Feature visibility for standard users</h3>
        <ul className="feature-flags">
          {Object.entries(flags).map(([key, enabled]) => (
            <li key={key}>
              <label>
                <input type="checkbox" checked={enabled} onChange={() => toggleFlag(key)} />
                {key.replace(/_/g, " ")}
              </label>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h3>Users</h3>
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
                <td>{u.first_name} {u.last_name}</td>
                <td>{u.email}</td>
                <td>{u.role}</td>
                <td>
                  <button onClick={() => resetPassword(u.id)}>Reset password</button>
                  <button onClick={() => removeUser(u.id)}>Remove</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
