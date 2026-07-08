import { useState } from "react";
import { api, setToken } from "../api";

export default function Login({ onLogin }) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("drift-sentinel-admin");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await api.login(username, password);
      if (data.access_token) {
        setToken(data.access_token);
        onLogin();
      } else {
        setError("Invalid credentials");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "40px", width: "380px" }}>
        <div style={{ marginBottom: 32 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--accent)", marginBottom: 4 }}>⬡ Drift Sentinel</h1>
          <p style={{ color: "var(--text2)", fontSize: 13 }}>ML monitoring platform</p>
        </div>
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <label style={{ display: "block", color: "var(--text2)", fontSize: 12, marginBottom: 6 }}>USERNAME</label>
            <input value={username} onChange={e => setUsername(e.target.value)}
              style={{ width: "100%", background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 6, padding: "10px 12px", color: "var(--text)", outline: "none" }} />
          </div>
          <div>
            <label style={{ display: "block", color: "var(--text2)", fontSize: 12, marginBottom: 6 }}>PASSWORD</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)}
              style={{ width: "100%", background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 6, padding: "10px 12px", color: "var(--text)", outline: "none" }} />
          </div>
          {error && <p style={{ color: "var(--danger)", fontSize: 13 }}>{error}</p>}
          <button type="submit" disabled={loading}
            style={{ background: "var(--accent)", color: "#fff", border: "none", borderRadius: 6, padding: "11px", fontWeight: 600, fontSize: 14, opacity: loading ? 0.7 : 1 }}>
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>
        <p style={{ marginTop: 20, color: "var(--text2)", fontSize: 12, textAlign: "center" }}>
          Default: admin / drift-sentinel-admin
        </p>
      </div>
    </div>
  );
}
