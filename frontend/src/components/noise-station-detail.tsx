"use client";

import { useEffect, useState, useCallback } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { X, RefreshCw } from "lucide-react";
import type { NoiseStation, NoiseHistoricalPoint } from "@/lib/types";
import { getNoiseComplianceColor, getNoiseComplianceLabel, ZONE_DISPLAY } from "@/lib/types";
import { getNoiseHistorical } from "@/lib/api";

interface NoiseStationDetailProps {
  station: NoiseStation;
  onClose: () => void;
}

interface ChartPoint {
  hour: string;
  hourLabel: string;
  Leq: number | null;
  Lmax: number | null;
  Lmin: number | null;
  dayLimit: number;
  nightLimit: number;
  activeLimit: number;
}

function formatHourLabel(hourStr: string): string {
  try {
    const d = new Date(hourStr);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
  } catch {
    return hourStr.slice(11, 16) || hourStr;
  }
}

function getActiveLimitForHour(hourStr: string, dayLimit: number, nightLimit: number): number {
  try {
    const d = new Date(hourStr);
    const h = d.getHours();
    return (h < 6 || h >= 22) ? nightLimit : dayLimit;
  } catch {
    return dayLimit;
  }
}

export function NoiseStationDetail({ station, onClose }: NoiseStationDetailProps) {
  const [historical, setHistorical] = useState<NoiseHistoricalPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getNoiseHistorical(station.station_id, 24);
      setHistorical(data.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch history");
    } finally {
      setLoading(false);
    }
  }, [station.station_id]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const complianceColor = getNoiseComplianceColor(station.leq, station.active_limit);
  const complianceLabel = getNoiseComplianceLabel(station.leq, station.active_limit);
  const zone = ZONE_DISPLAY[station.zone] || { label: station.zone, color: "#6b7280" };

  // Build chart data
  const chartData: ChartPoint[] = historical.map((pt) => {
    const dayLim = pt.day_limit || station.day_limit;
    const nightLim = pt.night_limit || station.night_limit;
    const activeLim = getActiveLimitForHour(pt.hour, dayLim, nightLim);
    return {
      hour: pt.hour,
      hourLabel: formatHourLabel(pt.hour),
      Leq: pt.Leq_avg ?? null,
      Lmax: pt.Lmax_avg ?? null,
      Lmin: pt.Lmin_avg ?? null,
      dayLimit: dayLim,
      nightLimit: nightLim,
      activeLimit: activeLim,
    };
  });

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Header */}
      <div className="p-3 border-b border-border flex items-center justify-between">
        <div className="min-w-0">
          <h3 className="text-sm font-bold truncate">{station.station_name}</h3>
          <p className="text-xs text-muted-foreground truncate">
            {station.station_id} &middot; {station.city}
          </p>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-md hover:bg-muted/50 transition-colors flex-shrink-0"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Zone + Compliance badges */}
      <div className="p-3 flex items-center gap-2 flex-wrap">
        <span
          className="px-2 py-0.5 rounded text-white text-xs font-medium"
          style={{ backgroundColor: zone.color }}
        >
          {zone.label} Zone
        </span>
        <span
          className="px-2 py-0.5 rounded text-white text-xs font-bold"
          style={{ backgroundColor: complianceColor }}
        >
          {complianceLabel}
        </span>
        <span className="text-xs text-muted-foreground ml-auto">
          {station.period === "night" ? "Night" : "Day"} Period
        </span>
      </div>

      {/* Current readings */}
      <div className="px-3 pb-3">
        <div className="grid grid-cols-3 gap-2">
          <div className="bg-muted/30 rounded-lg p-2 text-center">
            <div className="text-xs text-muted-foreground">Leq</div>
            <div className="text-lg font-bold" style={{ color: complianceColor }}>
              {station.leq}
            </div>
            <div className="text-[10px] text-muted-foreground">dB(A)</div>
          </div>
          <div className="bg-muted/30 rounded-lg p-2 text-center">
            <div className="text-xs text-muted-foreground">Lmax</div>
            <div className="text-lg font-bold">{station.lmax}</div>
            <div className="text-[10px] text-muted-foreground">dB(A)</div>
          </div>
          <div className="bg-muted/30 rounded-lg p-2 text-center">
            <div className="text-xs text-muted-foreground">Lmin</div>
            <div className="text-lg font-bold">{station.lmin}</div>
            <div className="text-[10px] text-muted-foreground">dB(A)</div>
          </div>
        </div>

        {/* Limit info */}
        <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
          <span>
            Limit: <strong>{station.active_limit} dB(A)</strong>
          </span>
          <span>
            Day: {station.day_limit} / Night: {station.night_limit}
          </span>
        </div>
        {station.exceedance_db > 0 && (
          <div className="mt-1 text-xs font-medium" style={{ color: "#dc2626" }}>
            Exceeding limit by +{station.exceedance_db} dB(A)
          </div>
        )}
      </div>

      {/* 24h Historical Chart */}
      <div className="px-3 pb-3 flex-1 min-h-[220px]">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs font-medium text-muted-foreground">
            24-Hour Noise Trend
          </h4>
          <button
            onClick={fetchHistory}
            className="p-1 rounded hover:bg-muted/50 transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-3 h-3 text-muted-foreground" />
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-[180px]">
            <RefreshCw className="w-5 h-5 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-[180px] text-xs text-destructive">
            {error}
          </div>
        ) : chartData.length === 0 ? (
          <div className="flex items-center justify-center h-[180px] text-xs text-muted-foreground">
            No historical data available
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData} margin={{ top: 5, right: 5, left: -10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis
                dataKey="hourLabel"
                tick={{ fontSize: 10 }}
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fontSize: 10 }}
                domain={["dataMin - 5", "dataMax + 5"]}
                label={{ value: "dB(A)", angle: -90, position: "insideLeft", style: { fontSize: 10 } }}
              />
              <Tooltip
                contentStyle={{
                  fontSize: 11,
                  borderRadius: 8,
                  border: "1px solid #e2e8f0",
                }}
                formatter={(value: unknown, name: unknown) => [
                  `${value} dB(A)`,
                  String(name),
                ]}
                labelFormatter={(label: unknown) => `Time: ${label}`}
              />
              {/* CPCB limit stepped line */}
              <Line
                type="stepAfter"
                dataKey="activeLimit"
                stroke="#dc2626"
                strokeWidth={2}
                strokeDasharray="6 3"
                dot={false}
                name="CPCB Limit"
                isAnimationActive={false}
              />
              {/* Leq line */}
              <Line
                type="monotone"
                dataKey="Leq"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={false}
                name="Leq (avg)"
                connectNulls
              />
              {/* Lmax line */}
              <Line
                type="monotone"
                dataKey="Lmax"
                stroke="#f97316"
                strokeWidth={1}
                dot={false}
                name="Lmax"
                connectNulls
                opacity={0.6}
              />
              {/* Lmin line */}
              <Line
                type="monotone"
                dataKey="Lmin"
                stroke="#22c55e"
                strokeWidth={1}
                dot={false}
                name="Lmin"
                connectNulls
                opacity={0.6}
              />
            </LineChart>
          </ResponsiveContainer>
        )}

        {/* Chart legend */}
        {!loading && !error && chartData.length > 0 && (
          <div className="flex flex-wrap gap-3 mt-1 justify-center">
            {[
              { color: "#3b82f6", label: "Leq (avg)" },
              { color: "#f97316", label: "Lmax" },
              { color: "#22c55e", label: "Lmin" },
              { color: "#dc2626", label: "CPCB Limit", dashed: true },
            ].map((item) => (
              <div key={item.label} className="flex items-center gap-1 text-[10px] text-muted-foreground">
                <span
                  className="inline-block w-3 h-0.5"
                  style={{
                    backgroundColor: item.color,
                    borderTop: item.dashed ? `2px dashed ${item.color}` : undefined,
                    height: item.dashed ? 0 : 2,
                  }}
                />
                {item.label}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Timestamp */}
      <div className="px-3 pb-3 text-[10px] text-muted-foreground text-right">
        Last reading: {new Date(station.timestamp).toLocaleString()}
      </div>
    </div>
  );
}
