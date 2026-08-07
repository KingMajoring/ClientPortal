import { createContext, useContext, useEffect, useState } from "react";
import { api } from "../shared/api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/auth/me")
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  async function login(email, password) {
    const loggedInUser = await api.post("/auth/login", { email, password });
    setUser(loggedInUser);
    return loggedInUser;
  }

  async function logout() {
    await api.post("/auth/logout", {});
    setUser(null);
  }

  return <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}

export const WGTK_ROLES = ["WGTK_ADMIN", "WGTK_GENERAL"];
export const CLIENT_ROLES = ["CLIENT_ADMIN", "CLIENT_GENERAL"];
