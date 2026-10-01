import { createContext, useMemo, useState, type ReactNode } from "react";
import { api } from "../api/client";

export interface AuthContextValue {
  token: string | null;
  login: (employeeId: number) => Promise<void>;
  logout: () => void;
}

// Token lives in memory only (React state), not localStorage/sessionStorage,
// to limit the blast radius if an XSS ever slipped past React's default
// escaping (relevant once self-report free text renders on this dashboard).
// It's lost on refresh — acceptable for the dev-login stub this backs;
// a real OIDC flow will use its own session handling.
export const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      login: async (employeeId: number) => {
        const { access_token: accessToken } = await api.devLogin(employeeId);
        setToken(accessToken);
      },
      logout: () => setToken(null),
    }),
    [token],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
