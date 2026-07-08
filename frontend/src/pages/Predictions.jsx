import { useEffect, useState } from "react";
import { api } from "../api";

export default function Predictions({ model }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!model) return;
    setLoading(true);
    api.predictions.list(model.id)
      .then(setLogs)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [model?.id]);

  if (!model) return <Placeholder />;

  const features = model.feature_schema ? Object.keys(model.feature_schema) : [];

  return (
    <div style={{ padding: 32, flex: 1, overflowY: "auto" }}>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 20, fontWeight: 700 }}>Prediction Logs</h2>
        <p style={{ color: "var(--text2)", marginTop: 4 }}>{logs.length} most recent predictions for {model.name}</p>
      </div>

      {loading ? (
        <div style={{ color: "var(--text2)" }}>Loading...</div>
      ) : (
        <div style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: "var(--radius)", overflow: "hidden" }}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "var(--bg3)", borderBottom: "1px solid var(--border)" }}>
                  <th style={th}>Timestamp</th>
                  {features.map(f => <th key={f} style={th}>{f}</th>)}
                  <th style={th}>Prediction</th>
                  <th style={th}>Probability</th>
                  <th style={th}>Ground Truth</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log, i) => (
                  <tr key={log.id} style={{ borderBottom: "1px solid var(--border)", background: i % 2 === 0 ? "transparent" : "var(--bg3)" }}>
                    <td style={td}>{new Date(log.ts).toLocaleString()}</td>
                    {features.map(f => (
                      <td key={f} style={td}>{log.features?.[f] ?? "—"}</td>
                    ))}
                    <td style={{ ...td, fontWeight: 600, color: log.prediction >= 0.5 ? "var(--success)" : "var(--danger)" }}>
                      {log.prediction}
                    </td>
                    <td style={td}>{log.prediction_proba != null ? (log.prediction_proba * 100).toFixed(1) + "%" : "—"}</td>
                    <td style={{ ...td, color: log.ground_truth != null ? "var(--accent2)" : "var(--text2)" }}>
                      {log.ground_truth ?? "pending"}
                    </td>
                  </tr>
                ))}
                {logs.length === 0 && (
                  <tr><td colSpan={4 + features.length} style={{ ...td, textAlign: "center", color: "var(--text2)", padding: 40 }}>
                    No predictions yet — run the simulator
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

const th = { padding: "12px 16px", textAlign: "left", color: "var(--text2)", fontWeight: 600, fontSize: 11, textTransform: "uppercase", letterSpacing: 0.5, whiteSpace: "nowrap" };
const td = { padding: "10px 16px", color: "var(--text)", whiteSpace: "nowrap" };

function Placeholder() {
  return <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text2)" }}>Select a model first</div>;
}
