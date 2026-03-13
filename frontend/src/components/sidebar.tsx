"use client";

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

  return (
    <aside className="w-64 flex-shrink-0 border-r border-border bg-card flex flex-col">
      {/* Logo */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <Leaf className="w-5 h-5 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-foreground tracking-tight">
              PRITHVINET
            </h1>
            <p className="text-xs text-muted-foreground">
              Environmental Monitor
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary/15 text-primary"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
              )}
            >
              <item.icon className="w-4 h-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-border">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Wind className="w-3 h-3" />
          <span>CECB Hackathon 2026</span>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          591 CPCB Stations | All India
        </p>
      </div>
    </aside>
  );
}
