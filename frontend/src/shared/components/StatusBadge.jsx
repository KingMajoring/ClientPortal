const COLOR_BY_STATUS = {
  NEW: "blue",
  QUOTED: "amber",
  ACCEPTED: "green",
  SCHEDULED: "blue",
  ETA_EXPIRED: "red",
  DECLINED_BY_CLIENT: "red",
  DECLINED_BY_WGTK: "red",
  COMPLETED: "gray",
};

export function StatusBadge({ status }) {
  const color = COLOR_BY_STATUS[status] || "gray";
  return <span className={`badge badge-${color}`}>{status.replace(/_/g, " ")}</span>;
}
