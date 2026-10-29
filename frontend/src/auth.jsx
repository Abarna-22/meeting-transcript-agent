import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api, setAuthToken } from "./api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const clearSession = () => {
      setAuthToken(null);
      setUser(null);
      setLoading(false);
    };
    window.addEventListener("auth:unauthorized", clearSession);
    if (!sessionStorage.getItem("meeting-intelligence-token")) {
      setLoading(false);
    } else {
      api.me()
        .then((account) => { if (active) setUser(account); })
        .catch(() => { if (active) clearSession(); })
        .finally(() => { if (active) setLoading(false); });
    }
    return () => {
      active = false;
      window.removeEventListener("auth:unauthorized", clearSession);
    };
  }, []);

  async function establishSession(createSession) {
    const session = await createSession();
    setAuthToken(session.access_token);
    setUser(session.user);
    return session.user;
  }

  async function signOut() {
    try {
      await api.signOut();
    } finally {
      setAuthToken(null);
      setUser(null);
    }
  }

  const value = useMemo(() => ({
    user,
    loading,
    signIn: (email, password) => establishSession(() => api.signIn(email, password)),
    signUp: (username, email, password) => establishSession(() => api.signUp(username, email, password)),
    signOut,
  }), [user, loading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider.");
  return context;
}
