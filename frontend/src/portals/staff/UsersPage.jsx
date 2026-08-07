import { useEffect, useState } from "react";
import { api } from "../../shared/api/client";

export function UsersPage() {
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState({ email: "", first_name: "", last_name: "", role: "WGTK_GENERAL" });
  const [tempPassword, setTempPassword] = useState(null);
  const [error, setError] = useState(null);

  function reload() {
    api.get("/staff/users").then(setUsers).catch((err) => setError(err.message));
  }

  useEffect(reload, []);

  function set(field) {
    return (e) => setForm({ ...form, [field]: e.target.value });
  }

  async function submit(e) {
    e.preventDefault();
    setError(null);
    try {
      const res = await api.post("/staff/users", form);
      setTempPassword(res.temp_password);
      reload();
    } catch (err) {
      setError(err.message);
    }
  }

  async function resetPassword(userId) {
    const res = await api.post(`/staff/users/${userId}/reset-password`, {});
    setTempPassword(res.temp_password);
  }

  async function removeUser(userId) {
    await api.del(`/staff/users/${userId}`);
    reload();
  }

  return (
    <div>
      <h2>WGTK staff users</h2>
      <form onSubmit={submit} className="onboard-form">
        <input placeholder="Email" type="email" value={form.email} onChange={set("email")} required />
        <input placeholder="First name" value={form.first_name} onChange={set("first_name")} required />
        <input placeholder="Last name" value={form.last_name} onChange={set("last_name")} required />
        <select value={form.role} onChange={set("role")}>
          <option value="WGTK_GENERAL">WGTK General</option>
          <option value="WGTK_ADMIN">WGTK Admin</option>
        </select>
        <button type="submit">Add staff user</button>
      </form>
      {error && <p className="form-error">{error}</p>}
      {tempPassword && <p className="form-success">Temp password: <code>{tempPassword}</code></p>}

      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Role</th>
            <th>Active</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id}>
              <td>{u.first_name} {u.last_name}</td>
              <td>{u.email}</td>
              <td>{u.role}</td>
              <td>{u.is_active ? "Yes" : "No"}</td>
              <td>
                <button onClick={() => resetPassword(u.id)}>Reset password</button>
                <button onClick={() => removeUser(u.id)}>Remove</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
