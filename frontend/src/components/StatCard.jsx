export default function StatCard({ label, value, sub, color = "var(--text)", icon }) {
  return (
    <div style={{
      background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: "var(--radius)",
      padding: "20px 24px", display: "flex", flexDirection: "column", gap: 6,
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: 12, color: "var(--text2)", textTransform: "uppercase", letterSpacing: 0.8 }}>{label}</span>
        {icon && <span style={{ fontSize: 18, opacity: 0.6 }}>{icon}</span>}
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, color }}>{value ?? "—"}</div>
      {sub && <div style={{ fontSize: 12, color: "var(--text2)" }}>{sub}</div>}
    </div>
  );
}
