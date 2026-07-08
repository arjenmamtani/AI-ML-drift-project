import { useEffect, useState } from "react";
import { api } from "../api";

export default function Health() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    api.health()
      .then(setHealth)
      .catch(e => setHealth({ status: "error", error: e.message }))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); const i = setInterval(load, 10000); return () => clearInterval(i); }, []);

  const services = health ? [
    { name: "API Server", status: health.status === "healthy" ? "ok" : "error", detail: `v${health.version || "?"}` },
    { name: "PostgreSQL / TimescaleDB", status: health.db, detail: "Time-series store" },
    { name: "Redis", status: health.redis, detail: "Celery broker" },
    { name: "MLflow", status: "ok", detail: "localhost:5001" },
  ] : [];

  return (
    <div style={{ padding: 32, flex: 1, overflowY: "auto" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 28 }}>
        <h2 style={{ fontSize: 20, fontWeight: 700 }}>System Health</h2>
        <button onClick={load} style={{ background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 7, padding: "8px 16px", color: "var(--text)", fontSize: 13 }}>
          ↻ Refresh
        </button>
      </div>

      {loading && !health ? (
        <div style={{ color: "var(--text2)" }}>Checking services...</div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16, maxWidth: 700 }}>
          {services.map(s => (
            <div key={s.name} style={{ background: "var(--bg2)", border: `1px solid ${s.status === "ok" ? "var(--border)" : "var(--danger)"}`, borderRadius: "var(--radius)", padding: "20px 24px" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                <span style={{ fontWeight: 600, fontSize: 14 }}>{s.name}</span>
                <span style={{
                  fontSize: 11, fontWeight: 700, padding: "3px 10px", borderRadius: 20,
                  background: s.status === "ok" ? "#6bcb7722" : "#ff6b6b22",
                  color: s.status === "ok" ? "var(--success)" : "var(--danger)",
                }}>
                  {s.status === "ok" ? "● HEALTHY" : "● " + s.status.toUpperCase()}
                </span>
              </div>
              <div style={{ fontSize: 12, color: "var(--text2)" }}>{s.detail}</div>
            </div>
          ))}
        </div>
      )}

      <div style={{ marginTop: 32, background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: 24, maxWidth: 700 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Quick Links</h3>
        <div style={{ display: "grid", gap: 10 }}>
          {[
            ["API Docs (Swagger)", "http://localhost:8000/docs"],
            ["API Docs (ReDoc)", "http://localhost:8000/redoc"],
            ["MLflow Experiments", "http://localhost:5001"],
            ["Health Check JSON", "http://localhost:8000/health"],
          ].map(([label, url]) => (
            <a key={url} href={url} target="_blank" rel="noreferrer"
              style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 16px", background: "var(--bg3)", borderRadius: 7, color: "var(--text)", fontSize: 13 }}>
              <span>{label}</span>
              <span style={{ color: "var(--accent)", fontSize: 11 }}>↗</span>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
