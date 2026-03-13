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
  Medal,
  GitCompareArrows,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

const navItems = [
  { href: "/", label: "Dashboard", icon: BarChart3 },
  { href: "/stations", label: "Stations", icon: MapPin },
  { href: "/rankings", label: "City Rankings", icon: Medal },
  { href: "/compare", label: "Compare Cities", icon: GitCompareArrows },
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
        "flex-shrink-0 border-r border-border bg-card flex flex-col transition-all duration-300 ease-in-out",
        collapsed ? "w-16" : "w-64"
      )}
    >
      {/* Logo */}
      <div className="p-3 border-b border-border">
        <div className="flex items-center gap-2 overflow-hidden">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center flex-shrink-0">
            <Leaf className="w-5 h-5 text-primary-foreground" />
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <h1 className="text-lg font-bold text-foreground tracking-tight leading-tight">
                PRITHVINET
              </h1>
              <p className="text-[10px] text-muted-foreground leading-tight">
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
                collapsed ? "justify-center px-2 py-2.5" : "px-3 py-2.5",
                isActive
                  ? "bg-primary/15 text-primary"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
              )}
            >
              <item.icon className="w-4 h-4 flex-shrink-0" />
              {!collapsed && <span className="truncate">{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Collapse Toggle */}
      <div className="p-2 border-t border-border">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className={cn(
            "flex items-center gap-2 w-full rounded-lg py-2 text-xs text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors",
            collapsed ? "justify-center px-2" : "px-3"
          )}
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
        <div className="p-3 border-t border-border">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Wind className="w-3 h-3" />
            <span>CECB Hackathon 2026</span>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            591 CPCB Stations | All India
          </p>
        </div>
      )}
    </aside>
  );
}
