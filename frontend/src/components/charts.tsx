"use client";

import type { AirReading } from "@/lib/types";
import { getAQIColor, getAQICategory, getAQIBgClass } from "@/lib/types";
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

interface PollutantChartProps {
  readings: AirReading[];
  stationId: string;
}

const POLLUTANT_LIMITS: Record<string, { naaqs: number; label: string }> = {
  "PM2.5": { naaqs: 60, label: "PM2.5 (ug/m3)" },
  PM10: { naaqs: 100, label: "PM10 (ug/m3)" },
  NO2: { naaqs: 80, label: "NO2 (ug/m3)" },
  SO2: { naaqs: 80, label: "SO2 (ug/m3)" },
  CO: { naaqs: 4, label: "CO (mg/m3)" },
  O3: { naaqs: 180, label: "O3 (ug/m3)" },
  NH3: { naaqs: 400, label: "NH3 (ug/m3)" },
  Pb: { naaqs: 1, label: "Pb (ug/m3)" },
};

function getBarColor(param: string, value: number): string {
  const limit = POLLUTANT_LIMITS[param];
  if (!limit) return "#64748b";
  const ratio = value / limit.naaqs;
  if (ratio <= 0.5) return "#22c55e";
  if (ratio <= 0.8) return "#84cc16";
  if (ratio <= 1.0) return "#eab308";
  if (ratio <= 1.5) return "#f97316";
  return "#ef4444";
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
    color: getBarColor(r.parameter, r.value),
  }));

  return (
    <ResponsiveContainer width="100%" height={250}>
      <BarChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis
          dataKey="name"
          tick={{ fill: "#94a3b8", fontSize: 11 }}
          axisLine={{ stroke: "#475569" }}
        />
        <YAxis
          tick={{ fill: "#94a3b8", fontSize: 11 }}
          axisLine={{ stroke: "#475569" }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#1e293b",
            border: "1px solid #475569",
            borderRadius: "0.5rem",
            color: "#e2e8f0",
          }}
          formatter={(value: unknown, name: unknown) => {
            const key = String(name ?? "");
            const limit = POLLUTANT_LIMITS[key];
            return [
              `${Number(value)} ${limit?.label?.split(" ").pop() || ""}`,
              key,
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

  const categoryCount: Record<string, number> = {};
  aqiReadings.forEach((r) => {
    const cat = getAQICategory(r.aqi);
    categoryCount[cat] = (categoryCount[cat] || 0) + 1;
  });

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
          <p
            className="text-3xl font-bold mt-1"
            style={{
              color: typeof stat.color === "string" && stat.color.startsWith("#")
                ? stat.color
                : undefined,
            }}
          >
            {stat.value}
          </p>
          <p className="text-xs text-muted-foreground mt-1">{stat.sub}</p>
        </div>
      ))}
    </div>
  );
}

// ── AQI Category Distribution ──────────────────────────────
export function AQICategoryBadges({ readings }: StatsCardsProps) {
  const aqiReadings = readings.filter((r) => r.parameter === "AQI");
  const categories = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"] as const;
  const counts: Record<string, number> = {};
  categories.forEach((c) => (counts[c] = 0));
  aqiReadings.forEach((r) => {
    const cat = getAQICategory(r.aqi);
    counts[cat] = (counts[cat] || 0) + 1;
  });

  const catColors: Record<string, string> = {
    Good: "bg-green-500/20 text-green-400 border-green-500/30",
    Satisfactory: "bg-lime-500/20 text-lime-400 border-lime-500/30",
    Moderate: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
    Poor: "bg-orange-500/20 text-orange-400 border-orange-500/30",
    "Very Poor": "bg-red-500/20 text-red-400 border-red-500/30",
    Severe: "bg-red-900/30 text-red-300 border-red-800/30",
  };

  return (
    <div className="flex flex-wrap gap-2">
      {categories.map((cat) =>
        counts[cat] > 0 ? (
          <span
            key={cat}
            className={`px-2.5 py-1 rounded-full text-xs font-medium border ${catColors[cat]}`}
          >
            {cat}: {counts[cat]}
          </span>
        ) : null
      )}
    </div>
  );
}

// ── Station List Table ─────────────────────────────────────
interface StationListProps {
  readings: AirReading[];
  onStationClick?: (stationId: string) => void;
}

export function StationList({ readings, onStationClick }: StationListProps) {
  const aqiReadings = readings
    .filter((r) => r.parameter === "AQI")
    .sort((a, b) => b.aqi - a.aqi);

  return (
    <div className="overflow-y-auto max-h-[400px]">
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-card">
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
            return (
              <tr
                key={r.station_id}
                className="border-t border-border/50 cursor-pointer hover:bg-muted/30 transition-colors"
                onClick={() => onStationClick?.(r.station_id)}
              >
                <td className="py-2 px-2 font-mono text-xs">
                  {r.station_id}
                </td>
                <td className="py-2 px-2">{r.city}</td>
                <td
                  className="py-2 px-2 text-right font-bold"
                  style={{ color }}
                >
                  {r.aqi}
                </td>
                <td className="py-2 px-2">
                  <span
                    className="px-1.5 py-0.5 rounded text-xs"
                    style={{
                      backgroundColor: color + "22",
                      color: color,
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
