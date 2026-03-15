"use client";

import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import type { WaterQualityHeatmapPoint } from "@/lib/types";

interface WaterStationListProps {
  points: WaterQualityHeatmapPoint[];
  onStationClick: (point: WaterQualityHeatmapPoint) => void;
  selectedStation?: WaterQualityHeatmapPoint | null;
  maxHeight?: string;
}

/** WQI category label */
function getWQICategory(wqi: number): string {
  if (wqi <= 0.15) return "Excellent";
  if (wqi <= 0.3) return "Good";
  if (wqi <= 0.5) return "Fair";
  if (wqi <= 0.7) return "Poor";
  return "Very Poor";
}

/** WQI category badge color */
function getWQIBadgeColor(wqi: number): string {
  if (wqi <= 0.15) return "#0571b0";
  if (wqi <= 0.3) return "#92c5de";
  if (wqi <= 0.5) return "#eab308";
  if (wqi <= 0.7) return "#f4a582";
  return "#ca0020";
}

/** Whether the badge text should be white (for dark backgrounds) */
function badgeTextWhite(wqi: number): boolean {
  return wqi <= 0.15 || wqi > 0.7;
}

export function WaterStationList({
  points,
  onStationClick,
  selectedStation,
  maxHeight = "510px",
}: WaterStationListProps) {
  const [search, setSearch] = useState("");

  // Sort by WQI descending (worst quality first), then filter by search
  const filtered = useMemo(() => {
    const sorted = [...points].sort((a, b) => b.wqi - a.wqi);
    if (!search.trim()) return sorted;
    const q = search.toLowerCase();
    return sorted.filter(
      (p) =>
        p.station_name.toLowerCase().includes(q) ||
        p.state.toLowerCase().includes(q) ||
        (p.district && p.district.toLowerCase().includes(q))
    );
  }, [points, search]);

  return (
    <div className="flex flex-col">
      {/* Search bar */}
      <div className="p-2 border-b border-border">
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search stations..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-7 pr-2 py-1.5 text-xs rounded-md border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>
      </div>

      {/* Station rows */}
      <div
        className="overflow-y-auto divide-y divide-border"
        style={{ maxHeight }}
      >
        {filtered.length === 0 && (
          <div className="p-4 text-xs text-muted-foreground text-center">
            No stations found.
          </div>
        )}
        {filtered.map((p) => {
          const isSelected =
            selectedStation &&
            selectedStation.lat === p.lat &&
            selectedStation.lng === p.lng;
          const color = getWQIBadgeColor(p.wqi);
          const white = badgeTextWhite(p.wqi);

          return (
            <button
              key={`${p.lat}-${p.lng}`}
              onClick={() => onStationClick(p)}
              className={`w-full text-left px-3 py-2 hover:bg-muted/40 transition-colors flex items-center gap-2 ${
                isSelected ? "bg-muted/50" : ""
              }`}
            >
              {/* WQI dot */}
              <div
                className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                style={{ backgroundColor: color }}
              />
              {/* Station info */}
              <div className="min-w-0 flex-1">
                <div className="text-xs font-medium truncate">
                  {p.station_name}
                </div>
                <div className="text-[10px] text-muted-foreground truncate">
                  {p.state}
                  {p.district ? ` \u00B7 ${p.district}` : ""}
                </div>
              </div>
              {/* WQI badge */}
              <span
                className="text-[10px] font-bold px-1.5 py-0.5 rounded flex-shrink-0"
                style={{
                  backgroundColor: color,
                  color: white ? "#fff" : "#1a1a1a",
                }}
              >
                {p.wqi.toFixed(3)}
              </span>
            </button>
          );
        })}
      </div>

      {/* Footer count */}
      <div className="p-2 border-t border-border text-[10px] text-muted-foreground text-center">
        {filtered.length} of {points.length} stations
        {search.trim() ? " (filtered)" : ""} &middot; Sorted by WQI (worst first)
      </div>
    </div>
  );
}
