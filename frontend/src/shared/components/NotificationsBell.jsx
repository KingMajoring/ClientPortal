import { useEffect, useState } from "react";
import { api } from "../api/client";

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
      <button onClick={() => setOpen((v) => !v)}>Notifications{unreadCount > 0 ? ` (${unreadCount})` : ""}</button>
      {open && (
        <div className="notifications-dropdown">
          {notifications.length === 0 && <p>No notifications yet.</p>}
          {notifications.map((n) => (
            <div key={n.id} className={`notification-row ${n.is_read ? "read" : "unread"}`} onClick={() => markRead(n.id)}>
              <p>{n.message}</p>
              <span>{new Date(n.created_at).toLocaleString()}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
