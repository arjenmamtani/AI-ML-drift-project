const NAV = [
  { id: "overview", label: "Overview", icon: "◈" },
  { id: "drift", label: "Drift Reports", icon: "⬡" },
  { id: "predictions", label: "Predictions", icon: "◎" },
  { id: "training", label: "Training", icon: "◆" },
  { id: "health", label: "System Health", icon: "◉" },
];

export default function Sidebar({ page, onPage, models, selectedModel, onModel }) {
  return (
    <aside style={{
      width: 220, background: "var(--bg2)", borderRight: "1px solid var(--border)",
      display: "flex", flexDirection: "column", padding: "24px 0", flexShrink: 0,
    }}>
      <div style={{ padding: "0 20px 24px", borderBottom: "1px solid var(--border)" }}>
        <div style={{ fontSize: 16, fontWeight: 700, color: "var(--accent)" }}>⬡ Drift Sentinel</div>
        <div style={{ fontSize: 11, color: "var(--text2)", marginTop: 2 }}>v0.2.0</div>
      </div>

      {models.length > 0 && (
        <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)" }}>
          <div style={{ fontSize: 11, color: "var(--text2)", marginBottom: 8, textTransform: "uppercase", letterSpacing: 1 }}>Model</div>
          <select value={selectedModel?.id || ""} onChange={e => onModel(models.find(m => m.id === e.target.value))}
            style={{ width: "100%", background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 6, padding: "7px 10px", color: "var(--text)", fontSize: 13 }}>
            {models.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
          </select>
        </div>
      )}

      <nav style={{ padding: "12px 12px", flex: 1 }}>
        {NAV.map(item => (
          <button key={item.id} onClick={() => onPage(item.id)}
            style={{
              width: "100%", display: "flex", alignItems: "center", gap: 10,
              padding: "9px 12px", borderRadius: 7, border: "none", textAlign: "left",
              background: page === item.id ? "var(--bg3)" : "transparent",
              color: page === item.id ? "var(--text)" : "var(--text2)",
              fontWeight: page === item.id ? 600 : 400, fontSize: 14,
              borderLeft: page === item.id ? "3px solid var(--accent)" : "3px solid transparent",
              marginBottom: 2,
            }}>
            <span style={{ fontSize: 16 }}>{item.icon}</span>
            {item.label}
          </button>
        ))}
      </nav>

      <div style={{ padding: "16px 20px", borderTop: "1px solid var(--border)" }}>
        <a href="http://localhost:5001" target="_blank" rel="noreferrer"
          style={{ fontSize: 12, color: "var(--text2)", display: "flex", alignItems: "center", gap: 6 }}>
          ↗ MLflow Dashboard
        </a>
      </div>
    </aside>
  );
}
