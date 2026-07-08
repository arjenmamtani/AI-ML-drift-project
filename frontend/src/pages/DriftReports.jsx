import { useEffect, useState } from "react";
import { api } from "../api";

export default function DriftReports({ model }) {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    if (!model) return;
    setLoading(true);
    api.drift.reports(model.id, 500)
      .then(setReports)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [model?.id]);

  if (!model) return <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text2)" }}>Select a model first</div>;

  const filtered = filter === "drifted" ? reports.filter(r => r.is_drifted) : filter === "stable" ? reports.filter(r => !r.is_drifted) : reports;

  return (
    <div style={{ padding: 32, flex: 1, overflowY: "auto" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700 }}>Drift Reports</h2>
          <p style={{ color: "var(--text2)", marginTop: 4 }}>{reports.length} reports for {model.name}</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {["all", "drifted", "stable"].map(f => (
            <button key={f} onClick={() => setFilter(f)}
              style={{ padding: "7px 16px", borderRadius: 7, border: "1px solid var(--border)", background: filter === f ? "var(--accent)" : "var(--bg3)", color: filter === f ? "#fff" : "var(--text2)", fontSize: 13, cursor: "pointer" }}>
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: "var(--radius)", overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: "var(--bg3)", borderBottom: "1px solid var(--border)" }}>
              {["Feature", "Test", "Score", "P-Value", "Threshold", "Status", "Samples", "Window End"].map(h => (
                <th key={h} style={{ padding: "12px 16px", textAlign: "left", color: "var(--text2)", fontWeight: 600, fontSize: 11, textTransform: "uppercase", letterSpacing: 0.5 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={8} style={{ padding: 40, textAlign: "center", color: "var(--text2)" }}>Loading...</td></tr>
            ) : filtered.length === 0 ? (
              <tr><td colSpan={8} style={{ padding: 40, textAlign: "center", color: "var(--text2)" }}>No reports found</td></tr>
            ) : filtered.map((r, i) => (
              <tr key={r.id} style={{ borderBottom: "1px solid var(--border)", background: i % 2 === 0 ? "transparent" : "#ffffff04" }}>
                <td style={{ padding: "10px 16px", fontWeight: 500 }}>{r.feature_name === "__prediction__" ? "prediction output" : r.feature_name}</td>
                <td style={{ padding: "10px 16px" }}>
                  <span style={{ background: "var(--bg3)", borderRadius: 4, padding: "2px 8px", fontSize: 11, fontFamily: "monospace" }}>{r.test_type.toUpperCase()}</span>
                </td>
                <td style={{ padding: "10px 16px", fontFamily: "monospace", color: r.is_drifted ? "var(--danger)" : "var(--text)" }}>{r.drift_score.toFixed(4)}</td>
                <td style={{ padding: "10px 16px", color: "var(--text2)" }}>{r.p_value != null ? r.p_value.toFixed(4) : "—"}</td>
                <td style={{ padding: "10px 16px", color: "var(--text2)" }}>{r.threshold}</td>
                <td style={{ padding: "10px 16px" }}>
                  <span style={{ padding: "3px 10px", borderRadius: 20, fontSize: 11, fontWeight: 700, background: r.is_drifted ? "#ff6b6b22" : "#6bcb7722", color: r.is_drifted ? "var(--danger)" : "var(--success)" }}>
                    {r.is_drifted ? "DRIFTED" : "STABLE"}
                  </span>
                </td>
                <td style={{ padding: "10px 16px", color: "var(--text2)" }}>{r.sample_size}</td>
                <td style={{ padding: "10px 16px", color: "var(--text2)", fontSize: 11 }}>{new Date(r.window_end).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
