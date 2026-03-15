"use client";

import { Suspense, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ShieldCheck,
  UserRound,
  Building2,
  Waves,
  Users,
  Landmark,
  Loader2,
} from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import type { UserRole } from "@/lib/types";

const ROLE_OPTIONS: Array<{
  role: UserRole;
  title: string;
  description: string;
  icon: typeof Landmark;
}> = [
  {
    role: "super_admin",
    title: "Super Admin",
    description: "Global platform access, user management, and AI copilot.",
    icon: ShieldCheck,
  },
  {
    role: "regional_officer",
    title: "Regional Officer",
    description: "Oversight for assigned regions and industry compliance.",
    icon: Landmark,
  },
  {
    role: "monitoring_team",
    title: "Monitoring Team",
    description: "Operational dashboard and alerts management.",
    icon: Waves,
  },
  {
    role: "industry_user",
    title: "Industry User",
    description: "Scoped to station data, notices, and compliance status for the linked unit.",
    icon: Building2,
  },
  {
    role: "citizen",
    title: "Citizen",
    description:
      "Public access with quick identity onboarding when submitting reports or earning eco points.",
    icon: Users,
  },
];

function LoginPortal() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath = searchParams.get("next") || "/";
  const { login, continueCitizen } = useAuth();

  const [selectedRole, setSelectedRole] = useState<UserRole>("super_admin");
  const [usernameOrEmail, setUsernameOrEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [city, setCity] = useState("Raipur");
  const [state, setState] = useState("Chhattisgarh");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const selectedRoleMeta = useMemo(
    () => ROLE_OPTIONS.find((item) => item.role === selectedRole) ?? ROLE_OPTIONS[0],
    [selectedRole]
  );

  async function handleRoleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const roleHome =
        selectedRole === "citizen"
          ? await continueCitizen({
              full_name: fullName.trim(),
              city: city.trim(),
              state: state.trim(),
              email: email.trim() || undefined,
              phone: phone.trim() || undefined,
            })
          : await login({
              username_or_email: usernameOrEmail.trim(),
              password,
              role: selectedRole,
            });
      router.push(nextPath || roleHome);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-[calc(100vh-3rem)] max-w-6xl flex-col justify-center gap-8 py-8">
      <div className="flex items-start justify-between gap-6">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.25em] text-muted-foreground">
            Government Access Portal
          </p>
          <h1 className="mt-2 text-5xl font-semibold tracking-tight text-foreground">
            Role-Based Access Control
          </h1>
          <p className="mt-3 max-w-3xl text-base text-muted-foreground">
            Authorized access for PRITHVINET operational users and public citizen onboarding.
            Select your category below to continue.
          </p>
        </div>
        <div className="hidden rounded-xl border border-border bg-card px-5 py-3 text-right shadow-sm md:block">
          <div className="text-sm font-medium tracking-[0.22em] text-muted-foreground">PrithviNET</div>
          <div className="mt-1 text-xs text-muted-foreground">
            Environmental Monitoring & Compliance Platform
          </div>
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
        {ROLE_OPTIONS.map((role) => {
          const Icon = role.icon;
          const active = role.role === selectedRole;
          return (
            <button
              key={role.role}
              type="button"
              onClick={() => {
                setSelectedRole(role.role);
                setError(null);
              }}
              className={`grid w-full grid-cols-[220px_1fr] items-center gap-4 border-b border-border px-6 py-5 text-left transition-colors last:border-b-0 ${
                active ? "bg-primary/8" : "bg-card hover:bg-muted/25"
              }`}
            >
              <div className="flex items-center gap-3 text-2xl font-medium text-foreground">
                <Icon className="h-6 w-6 text-primary" />
                <span>{role.title}</span>
              </div>
              <div className="text-lg text-muted-foreground">{role.description}</div>
            </button>
          );
        })}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
          <div className="mb-5 flex items-center gap-3">
            <selectedRoleMeta.icon className="h-5 w-5 text-primary" />
            <div>
              <h2 className="text-xl font-semibold text-foreground">{selectedRoleMeta.title} Sign-In</h2>
              <p className="text-sm text-muted-foreground">{selectedRoleMeta.description}</p>
            </div>
          </div>

          <form onSubmit={handleRoleLogin} className="space-y-4">
            {selectedRole === "citizen" ? (
              <>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Full Name
                    </label>
                    <input
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="Enter your name"
                      required
                      className="w-full rounded-lg border border-border bg-card px-3 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                    />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      City
                    </label>
                    <input
                      value={city}
                      onChange={(e) => setCity(e.target.value)}
                      placeholder="City"
                      required
                      className="w-full rounded-lg border border-border bg-card px-3 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                    />
                  </div>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      State
                    </label>
                    <input
                      value={state}
                      onChange={(e) => setState(e.target.value)}
                      placeholder="State"
                      required
                      className="w-full rounded-lg border border-border bg-card px-3 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                    />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Mobile or Email
                    </label>
                    <input
                      value={phone || email}
                      onChange={(e) => {
                        const val = e.target.value;
                        if (val.includes("@")) {
                          setEmail(val);
                          setPhone("");
                        } else {
                          setPhone(val);
                          setEmail("");
                        }
                      }}
                      placeholder="Optional contact"
                      className="w-full rounded-lg border border-border bg-card px-3 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                    />
                  </div>
                </div>
              </>
            ) : (
              <>
                <div>
                  <label className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Username or Official Email
                  </label>
                  <input
                    value={usernameOrEmail}
                    onChange={(e) => setUsernameOrEmail(e.target.value)}
                    placeholder="Enter username or email"
                    required
                    className="w-full rounded-lg border border-border bg-card px-3 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Password
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter password"
                    required
                    className="w-full rounded-lg border border-border bg-card px-3 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                  />
                </div>
              </>
            )}

            {error && (
              <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserRound className="h-4 w-4" />}
              {loading ? "Authorizing..." : selectedRole === "citizen" ? "Continue as Citizen" : "Sign In"}
            </button>
          </form>
        </div>

        <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-foreground">Demo Access Notes</h2>
          <div className="mt-4 space-y-4 text-sm text-muted-foreground">
            <div className="rounded-xl border border-border bg-muted/20 p-4">
              <div className="font-medium text-foreground">Internal demo accounts</div>
              <div className="mt-2 space-y-1">
                <div>`super.admin` / `superadmin123`</div>
                <div>`regional.officer.cg` / `regional123`</div>
                <div>`monitoring.team` / `monitor123`</div>
                <div>`industry.user` / `industry123`</div>
              </div>
            </div>
            <div className="rounded-xl border border-border bg-muted/20 p-4">
              <div className="font-medium text-foreground">Citizen access</div>
              <p className="mt-2">
                Citizens can browse publicly without credentials. A quick access profile is created only when a report submission or gamification action requires authentication.
              </p>
            </div>
            <div className="rounded-xl border border-border bg-muted/20 p-4">
              <div className="font-medium text-foreground">Portal style</div>
              <p className="mt-2">
                This login page intentionally follows a clean government-portal pattern: restrained palette, clear labels, and a structured role table rather than app-style promotional cards.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="px-6 py-10 text-sm text-muted-foreground">Loading access portal...</div>}>
      <LoginPortal />
    </Suspense>
  );
}
