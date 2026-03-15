"use client";

import type { WaterQualityHeatmapPoint } from "@/lib/types";

interface WaterStationDetailProps {
  point: WaterQualityHeatmapPoint;
  onClose: () => void;
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

// ── BIS / CPCB standard limits for water quality parameters ──
// { displayName: { desirable, max, unit, inverse } }
// inverse = true means LOWER values are worse (e.g. DO, pH)
interface ParamStandard {
  desirable: number;
  max: number;
  unit: string;
  inverse?: boolean; // true = higher is better (DO, DO Saturation)
  ranged?: [number, number]; // acceptable range (pH)
}

const PARAM_STANDARDS: Record<string, ParamStandard> = {
  "pH (field)":              { desirable: 8.5, max: 9.0, unit: "", ranged: [6.5, 8.5] },
  "pH (general)":            { desirable: 8.5, max: 9.0, unit: "", ranged: [6.5, 8.5] },
  "Temperature (C)":         { desirable: 30, max: 40, unit: "°C" },
  "DO (mg/L)":               { desirable: 6, max: 4, unit: "mg/L", inverse: true },
  "DO Saturation (%)":       { desirable: 80, max: 50, unit: "%", inverse: true },
  "BOD (mg/L)":              { desirable: 2, max: 3, unit: "mg/L" },
  "COD (mg/L)":              { desirable: 10, max: 25, unit: "mg/L" },
  "Total Coliform (MPN)":    { desirable: 50, max: 5000, unit: "MPN" },
  "Fecal Coliform (MPN)":    { desirable: 20, max: 2500, unit: "MPN" },
  "Conductivity (µS/cm)":    { desirable: 750, max: 2250, unit: "µS/cm" },
  "Nitrate-N (mg/L)":        { desirable: 10, max: 45, unit: "mg/L" },
  "TDS (mg/L)":              { desirable: 500, max: 2000, unit: "mg/L" },
  "Turbidity (NTU)":         { desirable: 5, max: 25, unit: "NTU" },
  "Susp. Solids (mg/L)":     { desirable: 25, max: 100, unit: "mg/L" },
  "Chloride (mg/L)":         { desirable: 250, max: 1000, unit: "mg/L" },
  "Sulphate (mg/L)":         { desirable: 200, max: 400, unit: "mg/L" },
  "Total Hardness":          { desirable: 200, max: 600, unit: "mg/L" },
};

/**
 * Get a ratio (0–1+) indicating how bad a parameter value is.
 *   0 = well within desirable limits
 *   1 = at maximum permissible limit
 *   >1 = exceeding limit
 */
function getParamRatio(name: string, value: number): number | null {
  const std = PARAM_STANDARDS[name];
  if (!std) return null;

  // Ranged parameter (pH): deviation from acceptable range
  if (std.ranged) {
    const [lo, hi] = std.ranged;
    if (value >= lo && value <= hi) return 0; // within range
    const deviation = value < lo ? lo - value : value - hi;
    const maxDeviation = std.max - hi; // how far max limit is from desirable edge
    return maxDeviation > 0 ? Math.min(deviation / maxDeviation, 2) : 1;
  }

  // Inverse parameter (DO): lower is worse
  if (std.inverse) {
    if (value >= std.desirable) return 0;
    if (value <= 0) return 2;
    // desirable=6, max(bad threshold)=4: ratio grows as value drops
    const range = std.desirable - std.max;
    if (range <= 0) return 0;
    return Math.min((std.desirable - value) / range, 2);
  }

  // Normal parameter: higher is worse
  if (value <= std.desirable) {
    return std.desirable > 0 ? (value / std.desirable) * 0.5 : 0; // 0–0.5 = safe zone
  }
  const range = std.max - std.desirable;
  if (range <= 0) return 1;
  return 0.5 + ((value - std.desirable) / range) * 0.5; // 0.5–1.0 = concern zone
}

/** Color for a parameter based on its ratio */
function getParamColor(ratio: number | null): string {
  if (ratio === null) return "#6b7280"; // grey — no standard available
  if (ratio <= 0.4) return "#16a34a";   // green — safe
  if (ratio <= 0.7) return "#eab308";   // yellow — moderate
  if (ratio <= 1.0) return "#f97316";   // orange — approaching limit
  return "#dc2626";                     // red — exceeding limit
}

// ── WQI Circular Gauge (SVG) — mirrors AQI gauge style ─────
function WQIGauge({ wqi, size = 150 }: { wqi: number; size?: number }) {
  const color = getWQIBadgeColor(wqi);
  const category = getWQICategory(wqi);
  const white = badgeTextWhite(wqi);
  const radius = (size - 16) / 2;
  const circumference = 2 * Math.PI * radius;
  // WQI 0–1 mapped to 0–100%
  const pct = Math.min(wqi, 1);
  const dashOffset = circumference * (1 - pct);

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative">
        <svg width={size} height={size} className="transform -rotate-90">
          {/* Background ring */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="#d1d5db"
            strokeWidth={10}
          />
          {/* Colored WQI arc */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={10}
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            strokeLinecap="round"
            className="transition-all duration-700"
          />
          {/* Center fill */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius - 12}
            fill={color}
            opacity={0.15}
          />
        </svg>
        {/* Value overlay */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold" style={{ color }}>
            {wqi.toFixed(3)}
          </span>
          <span className="text-xs font-medium text-muted-foreground mt-0.5">
            WQI
          </span>
        </div>
      </div>
      {/* Category badge below */}
      <span
        className="px-3 py-1 rounded-full text-xs font-bold"
        style={{ backgroundColor: color, color: white ? "#fff" : "#1a1a1a" }}
      >
        {category}
      </span>
    </div>
  );
}

export function WaterStationDetail({ point, onClose }: WaterStationDetailProps) {
  const params = point.parameters ? Object.entries(point.parameters) : [];

  return (
    <div className="flex flex-col h-full">
      {/* Header — matches AQI panel style */}
      <div className="p-4 border-b border-border flex items-center justify-between">
        <div className="min-w-0">
          <h3 className="font-semibold text-foreground truncate">
            {point.station_name || "Unknown Station"}
          </h3>
          <p className="text-xs text-muted-foreground">
            {point.state}
            {point.district ? ` \u00B7 ${point.district}` : ""}
          </p>
        </div>
        <button
          onClick={onClose}
          className="text-xs text-muted-foreground hover:text-foreground px-2 py-1 rounded border border-border hover:bg-muted/50"
        >
          Close
        </button>
      </div>

      {/* Gauge + Meta — centered like AQI panel */}
      <div className="p-4 flex flex-col items-center gap-3">
        <WQIGauge wqi={point.wqi} size={150} />

        {/* Station code */}
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>
            Station: <strong className="text-foreground">{point.station_code}</strong>
          </span>
        </div>

        {/* Coordinates */}
        <p className="text-xs text-muted-foreground">
          {point.lat.toFixed(4)}&deg;N, {point.lng.toFixed(4)}&deg;E
        </p>
      </div>

      {/* Parameters table — color-coded with BIS limits + mini bars */}
      <div className="flex-1 overflow-y-auto px-4 pb-4">
        {params.length > 0 ? (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-muted-foreground uppercase border-b border-border">
                <th className="text-left py-2">Parameter</th>
                <th className="text-right py-2">Value</th>
                <th className="text-right py-2">Limit</th>
                <th className="text-center py-2 w-16">Level</th>
              </tr>
            </thead>
            <tbody>
              {params.map(([name, val]) => {
                const ratio = getParamRatio(name, val);
                const color = getParamColor(ratio);
                const std = PARAM_STANDARDS[name];
                const barPct = ratio !== null ? Math.min(ratio, 1) * 100 : 0;

                return (
                  <tr key={name} className="border-b border-border/30">
                    <td className="py-2 font-medium">{name}</td>
                    <td className="py-2 text-right font-mono text-xs">
                      <span style={{ color }}>
                        {typeof val === "number" ? val.toFixed(2) : val}
                      </span>
                    </td>
                    <td className="py-2 text-right font-mono text-xs text-muted-foreground">
                      {std
                        ? std.ranged
                          ? `${std.ranged[0]}–${std.ranged[1]}`
                          : std.inverse
                            ? `≥${std.desirable}`
                            : `≤${std.max}`
                        : "—"}
                    </td>
                    <td className="py-2">
                      {ratio !== null ? (
                        <div className="flex items-center justify-center">
                          <div className="w-12 h-2.5 bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all"
                              style={{
                                width: `${barPct}%`,
                                backgroundColor: color,
                              }}
                            />
                          </div>
                        </div>
                      ) : (
                        <span className="text-xs text-muted-foreground text-center block">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : (
          <p className="text-xs text-muted-foreground text-center py-4">
            No parameter data available for this station.
          </p>
        )}
      </div>
    </div>
  );
}
