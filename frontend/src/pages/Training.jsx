import { useState } from "react";
import { api } from "../api";

export default function Training({ model }) {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleTrain() {
    if (!model) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await api.train(model.id);
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  if (!model) return <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text2)" }}>Select a model first</div>;

  return (
    <div style={{ padding: 32, flex: 1, overflowY: "auto" }}>
      <div style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 4 }}>Training Pipeline</h2>
        <p style={{ color: "var(--text2)" }}>Retrain {model.name} on reconciled labeled data. Results are logged to MLflow.</p>
      </div>

      <div style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: 28, marginBottom: 24, maxWidth: 540 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>XGBoost Retraining</h3>
        <div style={{ display: "grid", gap: 12, marginBottom: 24 }}>
          <Row label="Model" value={model.name} />
          <Row label="Task type" value={model.task_type} />
          <Row label="Algorithm" value="XGBoost (n_estimators=100, max_depth=4)" />
          <Row label="Requires" value="Ground truth labels reconciled via PATCH /predictions/ground-truth" />
        </div>
        <button onClick={handleTrain} disabled={loading}
          style={{ background: loading ? "var(--bg3)" : "var(--accent)", border: "none", borderRadius: 8, padding: "12px 28px", color: loading ? "var(--text2)" : "#fff", fontWeight: 600, fontSize: 14 }}>
          {loading ? "Training... (this may take 20–30s)" : "▶ Start Training Run"}
        </button>
      </div>

      {error && (
        <div style={{ background: "#ff6b6b11", border: "1px solid var(--danger)", borderRadius: "var(--radius)", padding: "16px 20px", marginBottom: 20, color: "var(--danger)" }}>
          <strong>Error:</strong> {error}
          {error.includes("Insufficient") && (
            <div style={{ marginTop: 8, fontSize: 12, color: "var(--text2)" }}>
              Run the drift simulator first, then reconcile ground truth labels via the API.
            </div>
          )}
        </div>
      )}

      {result && (
        <div style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: 28 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
            <span style={{ color: "var(--success)", fontSize: 18 }}>✓</span>
            <h3 style={{ fontSize: 15, fontWeight: 600 }}>Training Complete</h3>
          </div>
          <div style={{ display: "grid", gap: 12, marginBottom: 24 }}>
            <Row label="MLflow Run ID" value={<code style={{ fontSize: 11, color: "var(--accent)" }}>{result.mlflow_run_id}</code>} />
            <Row label="Training samples" value={result.n_training_samples} />
            <Row label="Trained at" value={new Date(result.trained_at).toLocaleString()} />
          </div>

          <div style={{ marginBottom: 24 }}>
            <div style={{ fontSize: 12, color: "var(--text2)", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 12 }}>Evaluation Metrics</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
              {Object.entries(result.metrics || {}).map(([k, v]) => (
                <div key={k} style={{ background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 8, padding: "12px 20px", minWidth: 100 }}>
                  <div style={{ fontSize: 11, color: "var(--text2)", marginBottom: 4 }}>{k.toUpperCase()}</div>
                  <div style={{ fontSize: 22, fontWeight: 700, color: "var(--accent2)" }}>{(v * 100).toFixed(1)}{k === "rmse" ? "" : "%"}</div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <div style={{ fontSize: 12, color: "var(--text2)", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 12 }}>SHAP Feature Importance</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {Object.entries(result.feature_importance || {}).slice(0, 8).map(([feat, score], i) => {
                const max = Object.values(result.feature_importance)[0];
                const pct = (score / max) * 100;
                return (
                  <div key={feat}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                      <span style={{ fontSize: 13 }}>{feat}</span>
                      <span style={{ fontSize: 12, color: "var(--text2)" }}>{score.toFixed(4)}</span>
                    </div>
                    <div style={{ height: 6, background: "var(--bg3)", borderRadius: 3, overflow: "hidden" }}>
                      <div style={{ height: "100%", width: `${pct}%`, background: i === 0 ? "var(--accent)" : "var(--accent2)", borderRadius: 3, transition: "width 0.5s" }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div style={{ marginTop: 20, padding: "12px 16px", background: "var(--bg3)", borderRadius: 8, fontSize: 12, color: "var(--text2)" }}>
            Full run details at{" "}
            <a href="http://localhost:5001" target="_blank" rel="noreferrer" style={{ color: "var(--accent)" }}>
              MLflow Dashboard →
            </a>
          </div>
        </div>
      )}
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
      <div style={{ width: 140, fontSize: 12, color: "var(--text2)", flexShrink: 0, paddingTop: 2 }}>{label}</div>
      <div style={{ fontSize: 13, color: "var(--text)" }}>{value}</div>
    </div>
  );
}
