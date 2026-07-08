const BASE = "http://localhost:8000/api/v1";

let _token = localStorage.getItem("ds_token") || null;

export function setToken(t) {
  _token = t;
  localStorage.setItem("ds_token", t);
}

export function getToken() {
  return _token;
}

async function request(path, opts = {}) {
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  if (_token) headers["Authorization"] = `Bearer ${_token}`;
  const res = await fetch(`${BASE}${path}`, { ...opts, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  login: (u, p) => {
    const body = new URLSearchParams({ username: u, password: p });
    return fetch(`${BASE}/auth/token`, { method: "POST", body }).then(r => r.json());
  },
  models: {
    list: () => request("/models"),
    get: (id) => request(`/models/${id}`),
    create: (data) => request("/models", { method: "POST", body: JSON.stringify(data) }),
  },
  drift: {
    latest: (id) => request(`/models/${id}/drift/latest`),
    reports: (id, limit = 200) => request(`/models/${id}/drift/reports?limit=${limit}`),
    compute: (id) => request(`/models/${id}/drift/compute?window_hours=1&reference_hours_back=2`, { method: "POST" }),
  },
  predictions: {
    list: (id) => request(`/models/${id}/predictions?limit=500`),
  },
  train: (id) => request(`/models/${id}/train`, { method: "POST" }),
  health: () => fetch("http://localhost:8000/health").then(r => r.json()),
};
