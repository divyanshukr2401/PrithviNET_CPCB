"use client";

import { useState, useEffect } from "react";
import type { AirReading, RealStationData } from "@/lib/types";
import {
  getAQIColor,
  getAQICategory,
  getAQITextOnColor,
  CPCB_AQI_COLORS,
  CPCB_AQI_TEXT_COLORS,
  CPCB_AQI_HEALTH_IMPACTS,
  CPCB_AQI_RANGES,
  AQI_CATEGORIES_ORDERED,
} from "@/lib/types";
import type { AQICategory } from "@/lib/types";
import { getRealStationData } from "@/lib/api";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

// ── NAAQS pollutant limits ─────────────────────────────────
const POLLUTANT_LIMITS: Record<string, { naaqs: number; label: string; unit: string }> = {
  "PM2.5": { naaqs: 60, label: "PM2.5", unit: "\u00b5g/m\u00b3" },
  PM10: { naaqs: 100, label: "PM10", unit: "\u00b5g/m\u00b3" },
  NO2: { naaqs: 80, label: "NO\u2082", unit: "\u00b5g/m\u00b3" },
  SO2: { naaqs: 80, label: "SO\u2082", unit: "\u00b5g/m\u00b3" },
  CO: { naaqs: 4, label: "CO", unit: "mg/m\u00b3" },
  O3: { naaqs: 180, label: "O\u2083", unit: "\u00b5g/m\u00b3" },
  NH3: { naaqs: 400, label: "NH\u2083", unit: "\u00b5g/m\u00b3" },
  Pb: { naaqs: 1, label: "Pb", unit: "\u00b5g/m\u00b3" },
};

function getPollutantColor(param: string, value: number): string {
  const limit = POLLUTANT_LIMITS[param];
  if (!limit) return "#64748b";
  const ratio = value / limit.naaqs;
  if (ratio <= 0.5) return CPCB_AQI_COLORS.Good;
  if (ratio <= 0.8) return CPCB_AQI_COLORS.Satisfactory;
  if (ratio <= 1.0) return CPCB_AQI_COLORS.Moderate;
  if (ratio <= 1.5) return CPCB_AQI_COLORS.Poor;
  if (ratio <= 2.0) return CPCB_AQI_COLORS["Very Poor"];
  return CPCB_AQI_COLORS.Severe;
}

// ── AQI Circular Gauge (SVG) ───────────────────────────────
interface AQIGaugeProps {
  aqi: number;
  size?: number;
}

export function AQIGauge({ aqi, size = 160 }: AQIGaugeProps) {
  const color = getAQIColor(aqi);
  const textColor = getAQITextOnColor(aqi);
  const category = getAQICategory(aqi);
  const radius = (size - 16) / 2;
  const circumference = 2 * Math.PI * radius;
  // AQI 0-500 mapped to 0-100%
  const pct = Math.min(aqi / 500, 1);
  const dashOffset = circumference * (1 - pct);

  return (
    <div className="flex flex-col items-center gap-1">
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
        {/* Colored AQI arc */}
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
      {/* AQI value overlay */}
      <div
        className="absolute flex flex-col items-center justify-center"
        style={{ width: size, height: size }}
      >
        <span className="text-4xl font-bold" style={{ color }}>
          {aqi}
        </span>
        <span className="text-xs font-medium text-muted-foreground mt-0.5">AQI</span>
      </div>
      {/* Category badge below */}
      <span
        className="px-3 py-1 rounded-full text-xs font-bold"
        style={{ backgroundColor: color, color: textColor }}
      >
        {category}
      </span>
    </div>
  );
}

// ── Station Detail Panel (CPCB-style right panel) ──────────
interface StationDetailPanelProps {
  readings: AirReading[];
  stationId: string;
  stationName?: string;
  onClose: () => void;
}

export function StationDetailPanel({
  readings,
  stationId,
  stationName,
  onClose,
}: StationDetailPanelProps) {
  const [realData, setRealData] = useState<RealStationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch real data from data.gov.in when station changes
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setRealData(null);

    getRealStationData(stationId)
      .then((data) => {
        if (!cancelled) {
          setRealData(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [stationId]);

  // Determine data source: real API data or simulated fallback
  const isReal = realData?.quality_flag === "real";
  const dataSource = realData?.source || "historical_pattern_simulator";

  // Use real data if available, otherwise fall back to existing readings
  let aqiValue: number;
  let aqiCity: string;
  let aqiTimestamp: string;
  let pollutantRows: Array<{ parameter: string; value: number; unit: string; aqi: number }>;
  let apiStationName: string | null = null;
  let dominantPollutant: string = "";

  if (realData && realData.pollutants && Object.keys(realData.pollutants).length > 0) {
    // Use real data
    aqiValue = realData.aqi.value;
    aqiCity = realData.city;
    aqiTimestamp = realData.last_update;
    apiStationName = realData.api_station_name;
    dominantPollutant = realData.dominant_pollutant;
    pollutantRows = Object.entries(realData.pollutants).map(([param, data]) => ({
      parameter: param,
      value: data.value,
      unit: data.unit,
      aqi: data.aqi,
    }));
  } else {
    // Fallback to simulated readings
    const aqiReading = readings.find(
      (r) => r.station_id === stationId && r.parameter === "AQI"
    );
    const pollutantReadings = readings.filter(
      (r) => r.station_id === stationId && r.parameter !== "AQI"
    );

    if (!aqiReading) {
      return (
        <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
          No data for this station
        </div>
      );
    }

    aqiValue = aqiReading.aqi;
    aqiCity = aqiReading.city;
    aqiTimestamp = aqiReading.timestamp;
    pollutantRows = pollutantReadings.map((r) => ({
      parameter: r.parameter,
      value: r.value,
      unit: r.unit,
      aqi: r.aqi,
    }));
  }

  const category = getAQICategory(aqiValue);
  const color = getAQIColor(aqiValue);

  // Find prominent pollutant from pollutant rows
  if (!dominantPollutant) {
    let maxRatio = 0;
    pollutantRows.forEach((r) => {
      const limit = POLLUTANT_LIMITS[r.parameter];
      if (limit) {
        const ratio = r.value / limit.naaqs;
        if (ratio > maxRatio) {
          maxRatio = ratio;
          dominantPollutant = r.parameter;
        }
      }
    });
  }
  if (!dominantPollutant) dominantPollutant = "N/A";

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-border flex items-center justify-between">
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-foreground truncate">
            {stationName || stationId}
          </h3>
          <p className="text-xs text-muted-foreground">
            {aqiCity} &middot; {stationId}
          </p>
          {apiStationName && (
            <p className="text-xs text-muted-foreground mt-0.5 truncate" title={apiStationName}>
              CPCB: {apiStationName}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2 ml-2 flex-shrink-0">
          {/* Live / Simulated Badge */}
          {loading ? (
            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-muted text-muted-foreground animate-pulse">
              Loading...
            </span>
          ) : isReal ? (
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              LIVE
            </span>
          ) : (
            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-100 text-amber-800 border border-amber-300">
              SIMULATED
            </span>
          )}
          <button
            onClick={onClose}
            className="text-xs text-muted-foreground hover:text-foreground px-2 py-1 rounded border border-border hover:bg-muted/50"
          >
            Close
          </button>
        </div>
      </div>

      {/* Data source info */}
      {!loading && (
        <div className={`px-4 py-1.5 text-[10px] border-b border-border ${
          isReal
            ? "bg-emerald-50 text-emerald-700"
            : "bg-amber-50 text-amber-700"
        }`}>
          {isReal
            ? `Real-time data from data.gov.in (CPCB)`
            : error
              ? `Simulated data (API: ${error})`
              : `Simulated data (historical pattern model)`
          }
        </div>
      )}

      {/* Gauge + Meta */}
      <div className="p-4 flex flex-col items-center gap-3">
        <div className="relative">
          <AQIGauge aqi={aqiValue} size={150} />
        </div>

        {/* Prominent pollutant badge */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Prominent Pollutant:</span>
          <span
            className="px-2 py-0.5 rounded text-xs font-bold"
            style={{ backgroundColor: color, color: getAQITextOnColor(aqiValue) }}
          >
            {dominantPollutant}
          </span>
        </div>

        {/* Last updated */}
        <p className="text-xs text-muted-foreground">
          Updated: {new Date(aqiTimestamp).toLocaleString()}
        </p>
      </div>

      {/* Pollutant breakdown table */}
      <div className="flex-1 overflow-y-auto px-4 pb-4">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-muted-foreground uppercase border-b border-border">
              <th className="text-left py-2">Pollutant</th>
              <th className="text-right py-2">Value</th>
              <th className="text-right py-2">NAAQS</th>
              <th className="text-center py-2 w-20">Level</th>
            </tr>
          </thead>
          <tbody>
            {pollutantRows.map((r) => {
              const limit = POLLUTANT_LIMITS[r.parameter];
              const pColor = getPollutantColor(r.parameter, r.value);
              const ratio = limit ? r.value / limit.naaqs : 0;
              return (
                <tr key={r.parameter} className="border-b border-border/30">
                  <td className="py-2 font-medium">
                    {limit?.label || r.parameter}
                  </td>
                  <td className="py-2 text-right font-mono text-xs">
                    {r.value.toFixed(1)} <span className="text-muted-foreground">{limit?.unit || r.unit}</span>
                  </td>
                  <td className="py-2 text-right font-mono text-xs text-muted-foreground">
                    {limit?.naaqs ?? "—"}
                  </td>
                  <td className="py-2">
                    <div className="flex items-center gap-1.5 justify-center">
                      {/* Mini bar */}
                      <div className="w-12 h-2.5 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all"
                          style={{
                            width: `${Math.min(ratio * 100, 100)}%`,
                            backgroundColor: pColor,
                          }}
                        />
                      </div>
                      <span className="text-[10px] font-mono" style={{ color: pColor }}>
                        {(ratio * 100).toFixed(0)}%
                      </span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Pollutant Bar Chart ────────────────────────────────────
interface PollutantChartProps {
  readings: AirReading[];
  stationId: string;
}

export function PollutantChart({ readings, stationId }: PollutantChartProps) {
  const stationReadings = readings.filter(
    (r) => r.station_id === stationId && r.parameter !== "AQI"
  );

  if (stationReadings.length === 0) {
    return (
      <div className="text-muted-foreground text-sm">
        No pollutant data available
      </div>
    );
  }

  const chartData = stationReadings.map((r) => ({
    name: r.parameter,
    value: Number(r.value.toFixed(2)),
    unit: r.unit,
    limit: POLLUTANT_LIMITS[r.parameter]?.naaqs || 0,
    color: getPollutantColor(r.parameter, r.value),
  }));

  return (
    <ResponsiveContainer width="100%" height={250}>
      <BarChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#d1d5db" />
        <XAxis
          dataKey="name"
          tick={{ fill: "#5a6570", fontSize: 11 }}
          axisLine={{ stroke: "#9ca3af" }}
        />
        <YAxis
          tick={{ fill: "#5a6570", fontSize: 11 }}
          axisLine={{ stroke: "#9ca3af" }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#ffffff",
            border: "1px solid #d1d5db",
            borderRadius: "0.5rem",
            color: "#1a1a2e",
          }}
          formatter={(value: unknown, name: unknown) => {
            const key = String(name ?? "");
            const limit = POLLUTANT_LIMITS[key];
            return [
              `${Number(value)} ${limit?.unit || ""}`,
              limit?.label || key,
            ];
          }}
        />
        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// ── Stat Cards ─────────────────────────────────────────────
interface StatsCardsProps {
  readings: AirReading[];
}

export function StatsCards({ readings }: StatsCardsProps) {
  const aqiReadings = readings.filter((r) => r.parameter === "AQI");
  if (aqiReadings.length === 0) return null;

  const avgAqi = Math.round(
    aqiReadings.reduce((s, r) => s + r.aqi, 0) / aqiReadings.length
  );
  const maxAqi = Math.max(...aqiReadings.map((r) => r.aqi));
  const minAqi = Math.min(...aqiReadings.map((r) => r.aqi));

  const stats = [
    {
      label: "Stations Live",
      value: aqiReadings.length,
      sub: "monitored",
      color: "#60a5fa",
    },
    {
      label: "Average AQI",
      value: avgAqi,
      sub: getAQICategory(avgAqi),
      color: getAQIColor(avgAqi),
    },
    {
      label: "Worst AQI",
      value: maxAqi,
      sub: aqiReadings.find((r) => r.aqi === maxAqi)?.city || "",
      color: getAQIColor(maxAqi),
    },
    {
      label: "Best AQI",
      value: minAqi,
      sub: aqiReadings.find((r) => r.aqi === minAqi)?.city || "",
      color: getAQIColor(minAqi),
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="bg-card rounded-lg p-4 border border-border"
        >
          <p className="text-xs text-muted-foreground uppercase tracking-wider">
            {stat.label}
          </p>
          <p className="text-3xl font-bold mt-1" style={{ color: stat.color }}>
            {stat.value}
          </p>
          <p className="text-xs text-muted-foreground mt-1">{stat.sub}</p>
        </div>
      ))}
    </div>
  );
}

// ── AQI Category Badges (distribution) ─────────────────────
export function AQICategoryBadges({ readings }: StatsCardsProps) {
  const aqiReadings = readings.filter((r) => r.parameter === "AQI");
  const counts: Record<string, number> = {};
  AQI_CATEGORIES_ORDERED.forEach((c) => (counts[c] = 0));
  aqiReadings.forEach((r) => {
    const cat = getAQICategory(r.aqi);
    counts[cat] = (counts[cat] || 0) + 1;
  });

  return (
    <div className="flex flex-wrap gap-2">
      {AQI_CATEGORIES_ORDERED.map((cat) =>
        counts[cat] > 0 ? (
          <span
            key={cat}
            className="px-2.5 py-1 rounded-full text-xs font-medium border"
            style={{
              backgroundColor: CPCB_AQI_COLORS[cat] + "22",
              color: CPCB_AQI_COLORS[cat],
              borderColor: CPCB_AQI_COLORS[cat] + "44",
            }}
          >
            {cat}: {counts[cat]}
          </span>
        ) : null
      )}
    </div>
  );
}

// ── AQI Color Legend Table (CPCB-style) ────────────────────
export function AQIColorLegend() {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="bg-muted/30">
            <th className="text-center py-2 px-3 text-xs uppercase text-muted-foreground font-medium">AQI</th>
            <th className="text-center py-2 px-3 text-xs uppercase text-muted-foreground font-medium">Remark</th>
            <th className="text-center py-2 px-3 text-xs uppercase text-muted-foreground font-medium w-16">Color</th>
            <th className="text-left py-2 px-3 text-xs uppercase text-muted-foreground font-medium">Possible Health Impacts</th>
          </tr>
        </thead>
        <tbody>
          {AQI_CATEGORIES_ORDERED.map((cat) => (
            <tr key={cat} className="border-t border-border/30">
              <td className="text-center py-2 px-3 font-mono text-xs">{CPCB_AQI_RANGES[cat]}</td>
              <td className="text-center py-2 px-3 font-medium text-xs">{cat}</td>
              <td className="py-2 px-3">
                <div
                  className="w-full h-5 rounded"
                  style={{ backgroundColor: CPCB_AQI_COLORS[cat] }}
                />
              </td>
              <td className="py-2 px-3 text-xs text-muted-foreground">
                {CPCB_AQI_HEALTH_IMPACTS[cat]}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Station List Table ─────────────────────────────────────
interface StationListProps {
  readings: AirReading[];
  onStationClick?: (stationId: string) => void;
  stationNameMap?: Record<string, string>;
  selectedStationId?: string | null;
  maxHeight?: string;
}

export function StationList({
  readings,
  onStationClick,
  stationNameMap,
  selectedStationId,
  maxHeight = "400px",
}: StationListProps) {
  const aqiReadings = readings
    .filter((r) => r.parameter === "AQI")
    .sort((a, b) => b.aqi - a.aqi);

  return (
    <div className="overflow-y-auto" style={{ maxHeight }}>
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-card z-10">
          <tr className="text-muted-foreground text-xs uppercase">
            <th className="text-left py-2 px-2">Station</th>
            <th className="text-left py-2 px-2">City</th>
            <th className="text-right py-2 px-2">AQI</th>
            <th className="text-left py-2 px-2">Status</th>
          </tr>
        </thead>
        <tbody>
          {aqiReadings.map((r) => {
            const cat = getAQICategory(r.aqi);
            const color = getAQIColor(r.aqi);
            const textOnColor = getAQITextOnColor(r.aqi);
            const isSelected = r.station_id === selectedStationId;
            const displayName =
              stationNameMap?.[r.station_id] || r.station_id;
            return (
              <tr
                key={r.station_id}
                className={`border-t border-border/50 cursor-pointer hover:bg-muted/30 transition-colors ${
                  isSelected ? "bg-primary/10" : ""
                }`}
                onClick={() => onStationClick?.(r.station_id)}
              >
                <td className="py-2 px-2 text-xs" title={r.station_id}>
                  <span className="line-clamp-1">{displayName}</span>
                </td>
                <td className="py-2 px-2 text-xs">{r.city}</td>
                <td
                  className="py-2 px-2 text-right font-bold"
                  style={{ color }}
                >
                  {r.aqi}
                </td>
                <td className="py-2 px-2">
                  <span
                    className="px-1.5 py-0.5 rounded text-[10px] font-semibold"
                    style={{
                      backgroundColor: color,
                      color: textOnColor,
                    }}
                  >
                    {cat}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
