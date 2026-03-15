import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PUBLIC_PATHS = ["/login", "/_next", "/favicon.ico"];
const ROLE_RULES: Array<{ path: string; roles: string[] }> = [
  {
    path: "/reports",
    roles: ["super_admin", "regional_officer", "monitoring_team", "industry_user"],
  },
  {
    path: "/causal",
    roles: ["super_admin", "regional_officer"],
  },
  {
    path: "/compliance",
    roles: ["super_admin", "regional_officer", "monitoring_team", "industry_user"],
  },
];

function matchesPath(pathname: string, path: string): boolean {
  return pathname === path || pathname.startsWith(`${path}/`);
}

function decodeBase64Url(value: string): string {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
  return atob(padded);
}

async function getRoleFromToken(token: string | undefined): Promise<string | null> {
  if (!token) return null;

  const [payloadBase64, signatureBase64] = token.split(".");
  if (!payloadBase64 || !signatureBase64) return null;

  try {
    const secret = process.env.APP_AUTH_SECRET || "prithvinet_app_auth_secret_2026";
    if (!secret) {
      return null;
    }
    const key = await crypto.subtle.importKey(
      "raw",
      new TextEncoder().encode(secret),
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["sign"]
    );
    const expectedSignature = await crypto.subtle.sign(
      "HMAC",
      key,
      new TextEncoder().encode(payloadBase64)
    );
    const expectedSignatureBase64 = btoa(String.fromCharCode(...new Uint8Array(expectedSignature)))
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/g, "");

    if (expectedSignatureBase64 !== signatureBase64) {
      return null;
    }

    const json = JSON.parse(decodeBase64Url(payloadBase64)) as { role?: string; exp?: string };
    if (json.exp && new Date(json.exp).getTime() <= Date.now()) {
      return null;
    }
    return typeof json.role === "string" ? json.role : null;
  } catch {
    return null;
  }
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (PUBLIC_PATHS.some((path) => matchesPath(pathname, path))) {
    return NextResponse.next();
  }

  const matchedRule = ROLE_RULES.find((rule) => matchesPath(pathname, rule.path));
  if (!matchedRule) {
    return NextResponse.next();
  }

  const hasToken = request.cookies.get("prithvinet_auth_token")?.value;
  if (!hasToken) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  const userRole = await getRoleFromToken(hasToken);
  if (!userRole) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  if (userRole && matchedRule.roles.includes(userRole)) {
    return NextResponse.next();
  }

  const forbiddenUrl = new URL("/", request.url);
  forbiddenUrl.searchParams.set("accessDenied", matchedRule.path);
  return NextResponse.redirect(forbiddenUrl);
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|.*\\..*).*)"],
};
