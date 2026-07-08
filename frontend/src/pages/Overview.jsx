import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, LineChart, Line, CartesianGrid, Legend } from "recharts";
import { api } from "../api";
import StatCard from "../components/StatCard";

const COLORS = { drifted: "#ff6b6b", stable: "#6bcb77" };

export default function Overview({ model }) {
  const [drift, setDrift] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [computing, setComputing] = useState(false);
  const [error, setError] = useState(null);

  async function load() {
    if (!model) return;
    setLoading(true);
    setError(null);
    try {
      const [latest, reports] = await Promise.all([
        api.drift.latest(model.id),
        api.drift.reports(model.id, 200),
      ]);
      setDrift(latest);

      // Build time-series: group reports by window_end, count drifted features
      const byWindow = {};
      for (const r of reports) {
        const key = r.window_end?.slice(0, 16) || "unknown";
        if (!byWindow[key]) byWindow[key] = { time: key, drifted: 0, stable: 0 };
        r.is_drifted ? byWindow[key].drifted++ : byWindow[key].stable++;
      }
      setHistory(Object.values(byWindow).slice(-20));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleCompute() {
    if (!model) return;
    setComputing(true);
    try {
      await api.drift.compute(model.id);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setComputing(false);
    }
  }

  useEffect(() => { load(); }, [model?.id]);

  if (!model) return <Empty />;

  const driftedCount = drift?.drifted_features?.length ?? 0;
  const totalCount = drift?.total_features ?? 0;
  const driftRatio = drift?.drift_ratio ?? 0;
  const severity = driftRatio > 0.5 ? "Critical" : driftRatio > 0.2 ? "Warning" : "Healthy";
  const severityColor = driftRatio > 0.5 ? "var(--danger)" : driftRatio > 0.2 ? "var(--warn)" : "var(--success)";

  // Feature bar chart data
  const featureData = (drift?.reports || []).map(r => ({
    name: r.feature_name === "__prediction__" ? "prediction output" : r.feature_name,
    score: parseFloat(r.drift_score.toFixed(4)),
    drifted: r.is_drifted,
  }));

  return (
    <div style={{ padding: 32, flex: 1, overflowY: "auto" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 28 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 4 }}>{model.name}</h2>
          <span style={{ fontSize: 12, color: "var(--text2)", background: "var(--bg3)", padding: "3px 10px", borderRadius: 20 }}>{model.task_type}</span>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button onClick={load} disabled={loading}
            style={{ background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 7, padding: "9px 18px", color: "var(--text)", fontSize: 13 }}>
            {loading ? "Loading..." : "↻ Refresh"}
          </button>
          <button onClick={handleCompute} disabled={computing}
            style={{ background: "var(--accent)", border: "none", borderRadius: 7, padding: "9px 18px", color: "#fff", fontSize: 13, fontWeight: 600 }}>
            {computing ? "Running..." : "▶ Compute Drift"}
          </button>
        </div>
      </div>

      {error && <div style={{ background: "#ff6b6b22", border: "1px solid var(--danger)", borderRadius: 8, padding: "12px 16px", marginBottom: 24, color: "var(--danger)" }}>{error}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 28 }}>
        <StatCard label="Status" value={severity} color={severityColor} icon="◉" />
        <StatCard label="Drifted Features" value={`${driftedCount} / ${totalCount}`} color={driftedCount > 0 ? "var(--danger)" : "var(--success)"} icon="⬡" />
        <StatCard label="Drift Ratio" value={`${(driftRatio * 100).toFixed(1)}%`} color={severityColor} icon="◈" />
        <StatCard label="Task Type" value={model.task_type} icon="◆" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 24 }}>
        <div style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: 24 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 20, color: "var(--text2)" }}>DRIFT SCORE BY FEATURE</h3>
          {featureData.length === 0 ? (
            <div style={{ color: "var(--text2)", textAlign: "center", padding: 40 }}>No drift data yet — run Compute Drift</div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={featureData} layout="vertical" margin={{ left: 60 }}>
                <XAxis type="number" tick={{ fill: "var(--text2)", fontSize: 11 }} />
                <YAxis type="category" dataKey="name" tick={{ fill: "var(--text2)", fontSize: 11 }} width={80} />
                <Tooltip contentStyle={{ background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 6 }} />
                <Bar dataKey="score" radius={[0, 4, 4, 0]}>
                  {featureData.map((d, i) => (
                    <Cell key={i} fill={d.drifted ? "var(--danger)" : "var(--accent2)"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        <div style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: 24 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 20, color: "var(--text2)" }}>DRIFT HISTORY</h3>
          {history.length === 0 ? (
            <div style={{ color: "var(--text2)", textAlign: "center", padding: 40 }}>No history yet</div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={history}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="time" tick={{ fill: "var(--text2)", fontSize: 10 }} tickFormatter={t => t.slice(11)} />
                <YAxis tick={{ fill: "var(--text2)", fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 6 }} />
                <Legend />
                <Line type="monotone" dataKey="drifted" stroke="var(--danger)" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="stable" stroke="var(--success)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {drift?.drifted_features?.length > 0 && (
        <div style={{ background: "#ff6b6b11", border: "1px solid #ff6b6b44", borderRadius: "var(--radius)", padding: "16px 20px" }}>
          <div style={{ fontWeight: 600, color: "var(--danger)", marginBottom: 8 }}>⚠ Drifted Features</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {drift.drifted_features.map(f => (
              <span key={f} style={{ background: "#ff6b6b22", border: "1px solid #ff6b6b55", borderRadius: 20, padding: "3px 12px", fontSize: 12, color: "var(--danger)" }}>
                {f === "__prediction__" ? "prediction output" : f}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Empty() {
  return (
    <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text2)" }}>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>⬡</div>
        <div style={{ fontSize: 16 }}>Select or register a model to get started</div>
      </div>
    </div>
  );
}
