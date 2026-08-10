import { useEffect, useState } from "react";
import { api } from "../../shared/api/client";
import { Icon } from "../../shared/components/Icon";

const WGTK_SCOPE = "__wgtk__";

export function UsersPage() {
  const [clients, setClients] = useState([]);
  const [scope, setScope] = useState(WGTK_SCOPE);
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState({ email: "", first_name: "", last_name: "", role: "WGTK_GENERAL" });
  const [tempPassword, setTempPassword] = useState(null);
  const [error, setError] = useState(null);

  const isClientScope = scope !== WGTK_SCOPE;

  useEffect(() => {
    api.get("/staff/clients").then(setClients).catch(() => {});
  }, []);

  useEffect(() => {
    setForm({
      email: "",
      first_name: "",
      last_name: "",
      role: isClientScope ? "CLIENT_GENERAL" : "WGTK_GENERAL",
    });
    setTempPassword(null);
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scope]);

  function reload() {
    const params = isClientScope ? `?client_company_id=${scope}` : "";
    api.get(`/staff/users${params}`).then(setUsers).catch((err) => setError(err.message));
  }

  function set(field) {
    return (e) => setForm({ ...form, [field]: e.target.value });
  }

  async function submit(e) {
    e.preventDefault();
    setError(null);
    try {
      const body = isClientScope ? { ...form, client_company_id: scope } : form;
      const res = await api.post("/staff/users", body);
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

  const currentClientName = clients.find((c) => String(c.id) === String(scope))?.name;

  return (
    <div>
      <div className="page-header">
        <h2>Users</h2>
        <p className="subtitle">WGTK Admin manages staff accounts and every client company's users from here.</p>
      </div>

      <div className="list-filters">
        <select value={scope} onChange={(e) => setScope(e.target.value)}>
          <option value={WGTK_SCOPE}>WGTK staff</option>
          {clients.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </div>

      <section className="card">
        <div className="card-header">
          <div className="card-header-title">
            <div className="icon-badge">
              <Icon name="plus" size={16} />
            </div>
            <h3>{isClientScope ? `Add user for ${currentClientName}` : "Add staff user"}</h3>
          </div>
        </div>
        <form onSubmit={submit} className="onboard-form">
          <input placeholder="Email" type="email" value={form.email} onChange={set("email")} required />
          <input placeholder="First name" value={form.first_name} onChange={set("first_name")} required />
          <input placeholder="Last name" value={form.last_name} onChange={set("last_name")} required />
          <select value={form.role} onChange={set("role")}>
            {isClientScope ? (
              <>
                <option value="CLIENT_GENERAL">Standard user</option>
                <option value="CLIENT_ADMIN">Admin</option>
              </>
            ) : (
              <>
                <option value="WGTK_GENERAL">WGTK General</option>
                <option value="WGTK_ADMIN">WGTK Admin</option>
              </>
            )}
          </select>
          <button type="submit">{isClientScope ? "Add user" : "Add staff user"}</button>
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
              <th>Active</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.length === 0 && (
              <tr>
                <td colSpan={5} style={{ textAlign: "center", color: "var(--text-tertiary)", padding: "2rem" }}>
                  No users yet.
                </td>
              </tr>
            )}
            {users.map((u) => (
              <tr key={u.id}>
                <td style={{ fontWeight: 600 }}>{u.first_name} {u.last_name}</td>
                <td>{u.email}</td>
                <td><span className={`badge ${u.role.endsWith("ADMIN") ? "badge-blue" : "badge-gray"}`}>{u.role.replace(/^(WGTK|CLIENT)_/, "")}</span></td>
                <td>{u.is_active ? <span className="badge badge-green">Active</span> : <span className="badge badge-gray">Inactive</span>}</td>
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
