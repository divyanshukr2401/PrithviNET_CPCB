"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import {
  continueAsCitizen,
  getCurrentUser,
  login as loginRequest,
  logout as logoutRequest,
  refreshSession as refreshSessionRequest,
  storeAuthToken,
} from "@/lib/api";
import type { AuthenticatedUser, UserRole } from "@/lib/types";

type CitizenPayload = {
  full_name: string;
  city: string;
  state: string;
  email?: string;
  phone?: string;
};

type LoginPayload = {
  username_or_email: string;
  password: string;
  role: UserRole;
};

type AuthContextValue = {
  user: AuthenticatedUser | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (payload: LoginPayload) => Promise<string>;
  continueCitizen: (payload: CitizenPayload) => Promise<string>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  refreshSession: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [loading, setLoading] = useState(true);

  async function refreshUser() {
    try {
      const me = await getCurrentUser();
      setUser(me);
    } catch {
      storeAuthToken(null);
      setUser(null);
    }
  }

  async function refreshSession(): Promise<void> {
    try {
      const response = await refreshSessionRequest();
      storeAuthToken(response.access_token);
      setUser(response.user);
    } catch {
      await refreshUser();
    }
  }

  useEffect(() => {
    let cancelled = false;
    async function bootstrap() {
      try {
        const me = await getCurrentUser();
        if (!cancelled) {
          setUser(me);
        }

        try {
          const response = await refreshSessionRequest();
          if (!cancelled) {
            storeAuthToken(response.access_token);
            setUser(response.user);
          }
        } catch {
          // Keep the current session if refresh is temporarily unavailable.
        }
      } catch {
        if (!cancelled) {
          storeAuthToken(null);
          setUser(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  async function login(payload: LoginPayload): Promise<string> {
    const response = await loginRequest(payload);
    storeAuthToken(response.access_token);
    setUser(response.user);
    return response.role_home;
  }

  async function continueCitizen(payload: CitizenPayload): Promise<string> {
    const response = await continueAsCitizen(payload);
    storeAuthToken(response.access_token);
    setUser(response.user);
    return response.role_home;
  }

  async function logout(): Promise<void> {
    try {
      await logoutRequest();
    } catch {
      // no-op
    } finally {
      storeAuthToken(null);
      setUser(null);
    }
  }

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      isAuthenticated: !!user,
      login,
      continueCitizen,
      logout,
      refreshUser,
      refreshSession,
    }),
    [user, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
