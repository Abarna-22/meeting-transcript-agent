let authToken = sessionStorage.getItem("meeting-intelligence-token");

export function setAuthToken(token) {
  authToken = token;
  if (token) sessionStorage.setItem("meeting-intelligence-token", token);
  else sessionStorage.removeItem("meeting-intelligence-token");
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (authToken) headers.set("Authorization", `Bearer ${authToken}`);
  const res = await fetch(`/api${path}`, { ...options, headers });
  if (!res.ok) {
    if (res.status === 401 && authToken && !path.startsWith("/auth/")) {
      window.dispatchEvent(new Event("auth:unauthorized"));
    }
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) detail = body.detail.map((d) => d.msg).join("; ");
    } catch { /* non-JSON error body */ }
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

const json = (method, body) => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  health: () => request("/health"),
  signUp: (username, email, password) => request("/auth/signup", json("POST", { username, email, password })),
  signIn: (email, password) => request("/auth/signin", json("POST", { email, password })),
  signOut: () => request("/auth/signout", { method: "POST" }),
  me: () => request("/auth/me"),
  meetings: () => request("/meetings"),
  meeting: (id) => request(`/meetings/${id}`),
  createMeeting: (formData) => request("/meetings", { method: "POST", body: formData }),
  deleteMeeting: (id) => request(`/meetings/${id}`, { method: "DELETE" }),
  query: (payload) => request("/query", json("POST", payload)),
  decisions: () => request("/decisions"),
  actionItems: (params = {}) => request(`/action-items?${new URLSearchParams(params)}`),
  setActionStatus: (id, status) => request(`/action-items/${id}`, json("PATCH", { status })),
};

export const fmtDate = (iso) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
