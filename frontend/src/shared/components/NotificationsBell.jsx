import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Icon } from "./Icon";

export function NotificationsBell() {
  const [notifications, setNotifications] = useState([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    api.get("/shared/notifications").then(setNotifications).catch(() => {});
  }, []);

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  async function markRead(id) {
    const updated = await api.post(`/shared/notifications/${id}/read`, {});
    setNotifications((prev) => prev.map((n) => (n.id === id ? updated : n)));
  }

  return (
    <div className="notifications-bell">
      <button className="btn-secondary" onClick={() => setOpen((v) => !v)}>
        <Icon name="bell" size={16} />
        Notifications{unreadCount > 0 ? ` (${unreadCount})` : ""}
      </button>
      {open && (
        <div className="notifications-dropdown">
          {notifications.length === 0 && <p style={{ padding: "0.9rem", color: "var(--text-tertiary)", margin: 0 }}>No notifications yet.</p>}
          {notifications.map((n) => (
            <div key={n.id} className={`notification-row ${n.is_read ? "read" : "unread"}`} onClick={() => markRead(n.id)}>
              <p style={{ margin: "0 0 0.2rem" }}>{n.message}</p>
              <span>{new Date(n.created_at).toLocaleString()}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
