"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  BarChart3,
  Wind,
  Activity,
  BrainCircuit,
  Shield,
  Trophy,
  MapPin,
  Leaf,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

const navItems = [
  { href: "/", label: "Dashboard", icon: BarChart3 },
  { href: "/stations", label: "Stations", icon: MapPin },
  { href: "/forecast", label: "Forecast", icon: Activity },
  { href: "/causal", label: "What-If Simulator", icon: BrainCircuit },
  { href: "/compliance", label: "OCEMS Healer", icon: Shield },
  { href: "/gamification", label: "Eco Points", icon: Trophy },
];

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        "flex-shrink-0 flex flex-col transition-all duration-300 ease-in-out",
        collapsed ? "w-16" : "w-64"
      )}
      style={{
        backgroundColor: "var(--sidebar-bg)",
        color: "var(--sidebar-fg)",
        borderRight: "1px solid var(--sidebar-border)",
      }}
    >
      {/* Logo */}
      <div className="p-3" style={{ borderBottom: "1px solid var(--sidebar-border)" }}>
        <div className="flex items-center gap-2 overflow-hidden">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0" style={{ backgroundColor: "rgba(255,255,255,0.15)" }}>
            <Leaf className="w-5 h-5" style={{ color: "#4ade80" }} />
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <h1 className="text-lg font-bold tracking-tight leading-tight" style={{ color: "var(--sidebar-fg)" }}>
                PRITHVINET
              </h1>
              <p className="text-[10px] leading-tight" style={{ color: "rgba(226,232,240,0.6)" }}>
                Environmental Monitor
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-2 space-y-0.5 overflow-y-auto">
        {navItems.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              title={collapsed ? item.label : undefined}
              className={cn(
                "flex items-center gap-3 rounded-lg text-sm font-medium transition-colors",
                collapsed ? "justify-center px-2 py-2.5" : "px-3 py-2.5"
              )}
              style={{
                backgroundColor: isActive ? "var(--sidebar-active)" : "transparent",
                color: isActive ? "#ffffff" : "rgba(226,232,240,0.7)",
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = "var(--sidebar-active)";
                  e.currentTarget.style.color = "#ffffff";
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = "transparent";
                  e.currentTarget.style.color = "rgba(226,232,240,0.7)";
                }
              }}
            >
              <item.icon className="w-4 h-4 flex-shrink-0" />
              {!collapsed && <span className="truncate">{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Collapse Toggle */}
      <div className="p-2" style={{ borderTop: "1px solid var(--sidebar-border)" }}>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className={cn(
            "flex items-center gap-2 w-full rounded-lg py-2 text-xs transition-colors",
            collapsed ? "justify-center px-2" : "px-3"
          )}
          style={{ color: "rgba(226,232,240,0.6)" }}
          onMouseEnter={(e) => {
            e.currentTarget.style.color = "#ffffff";
            e.currentTarget.style.backgroundColor = "var(--sidebar-active)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.color = "rgba(226,232,240,0.6)";
            e.currentTarget.style.backgroundColor = "transparent";
          }}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <>
              <ChevronLeft className="w-4 h-4" />
              <span>Collapse</span>
            </>
          )}
        </button>
      </div>

      {/* Footer */}
      {!collapsed && (
        <div className="p-3" style={{ borderTop: "1px solid var(--sidebar-border)" }}>
          <div className="flex items-center gap-2 text-xs" style={{ color: "rgba(226,232,240,0.5)" }}>
            <Wind className="w-3 h-3" />
            <span>CECB Hackathon 2026</span>
          </div>
          <p className="text-xs mt-1" style={{ color: "rgba(226,232,240,0.5)" }}>
            591 CPCB Stations | All India
          </p>
        </div>
      )}
    </aside>
  );
}
