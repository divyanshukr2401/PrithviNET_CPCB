"use client";

import { useState } from "react";
import { getForecast } from "@/lib/api";
import type { ForecastResponse, ForecastPoint } from "@/lib/types";
import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Activity, RefreshCw } from "lucide-react";

const CG_STATIONS = [
  { id: "site_5503", city: "Bilaspur" },
  { id: "site_5536", city: "Bhilai" },
  { id: "site_5652", city: "Raipur" },
  { id: "site_5653", city: "Raipur" },
  { id: "site_5654", city: "Raipur" },
  { id: "site_5655", city: "Raipur" },
  { id: "site_5656", city: "Korba" },
  { id: "site_5657", city: "Korba" },
  { id: "site_5659", city: "Bhilai" },
  { id: "site_5660", city: "Bhilai" },
  { id: "site_5689", city: "Chhal" },
  { id: "site_5690", city: "Kunjemura" },
  { id: "site_5691", city: "Milupara" },
  { id: "site_5692", city: "Tumidih" },
];

function formatTimestamp(ts: string): string {
  const d = new Date(ts);
  return d.toLocaleString("en-IN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function formatMetricKey(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatMetricValue(value: unknown): string {
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(4);
  }
  return String(value);
}

interface ChartDataPoint extends ForecastPoint {
  label: string;
}

export default function ForecastPage() {
  const [selectedStation, setSelectedStation] = useState(CG_STATIONS[0].id);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getForecast({ station_id: selectedStation });
      setForecast(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate forecast");
      setForecast(null);
    } finally {
      setLoading(false);
    }
  };

  const chartData: ChartDataPoint[] =
    forecast?.forecast.map((pt) => ({
      ...pt,
      label: formatTimestamp(pt.timestamp),
    })) ?? [];

  const stationLabel =
    CG_STATIONS.find((s) => s.id === selectedStation)?.city ?? selectedStation;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Activity className="w-6 h-6 text-primary" />
          AQI Forecast
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Generate air quality index predictions for Chhattisgarh monitoring stations
        </p>
      </div>

      {/* Controls */}
      <div className="bg-card rounded-lg border border-border p-5">
        <h2 className="text-sm font-medium text-muted-foreground mb-4">
          Forecast Configuration
        </h2>
        <div className="flex flex-col sm:flex-row items-start sm:items-end gap-4">
          <div className="flex-1 w-full sm:w-auto">
            <label
              htmlFor="station-select"
              className="block text-xs font-medium text-muted-foreground mb-1.5"
            >
              Station
            </label>
            <select
              id="station-select"
              value={selectedStation}
              onChange={(e) => setSelectedStation(e.target.value)}
              className="w-full rounded-lg border border-border bg-card text-foreground px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
            >
              {CG_STATIONS.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.id} &mdash; {s.city}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={handleGenerate}
            disabled={loading}
            className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Activity className="w-4 h-4" />
            )}
            {loading ? "Generating..." : "Generate Forecast"}
          </button>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-card rounded-lg border border-red-500/30 p-5">
          <p className="text-red-400 font-medium text-sm">Forecast Error</p>
          <p className="text-muted-foreground text-sm mt-1">{error}</p>
        </div>
      )}

      {/* Empty State */}
      {!loading && !forecast && !error && (
        <div className="bg-card rounded-lg border border-border p-12 text-center">
          <Activity className="w-10 h-10 text-muted-foreground/40 mx-auto mb-3" />
          <p className="text-muted-foreground text-sm">
            Select a station and click <span className="text-foreground font-medium">Generate Forecast</span> to view AQI predictions.
          </p>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="bg-card rounded-lg border border-border p-12 text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-primary mx-auto mb-3" />
          <p className="text-muted-foreground text-sm">
            Generating forecast for {stationLabel}...
          </p>
        </div>
      )}

      {/* Forecast Results */}
      {forecast && !loading && (
        <div className="space-y-6">
          {/* Chart */}
          <div className="bg-card rounded-lg border border-border p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="font-medium">
                  {forecast.parameter} Forecast &mdash; {stationLabel}
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {forecast.horizon_hours}h horizon | Generated{" "}
                  {new Date(forecast.generated_at).toLocaleString("en-IN")}
                </p>
              </div>
              <span className="text-xs bg-primary/10 text-primary px-2.5 py-1 rounded-full font-medium">
                {forecast.model_used}
              </span>
            </div>

            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={380}>
                <ComposedChart
                  data={chartData}
                  margin={{ top: 10, right: 20, left: 10, bottom: 10 }}
                >
                  <defs>
                    <linearGradient id="confidenceFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.2} />
                      <stop offset="100%" stopColor="#3b82f6" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis
                    dataKey="label"
                    tick={{ fill: "#94a3b8", fontSize: 11 }}
                    tickLine={{ stroke: "#334155" }}
                    axisLine={{ stroke: "#334155" }}
                    interval="preserveStartEnd"
                    angle={-30}
                    textAnchor="end"
                    height={60}
                  />
                  <YAxis
                    tick={{ fill: "#94a3b8", fontSize: 11 }}
                    tickLine={{ stroke: "#334155" }}
                    axisLine={{ stroke: "#334155" }}
                    label={{
                      value: forecast.parameter,
                      angle: -90,
                      position: "insideLeft",
                      fill: "#94a3b8",
                      fontSize: 12,
                    }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#1e293b",
                      border: "1px solid #334155",
                      borderRadius: "8px",
                      color: "#e2e8f0",
                      fontSize: "12px",
                    }}
                    labelStyle={{ color: "#94a3b8", marginBottom: "4px" }}
                    formatter={(value: unknown, name: unknown) => {
                      const labels: Record<string, string> = {
                        predicted: "Predicted",
                        upper_bound: "Upper Bound",
                        lower_bound: "Lower Bound",
                      };
                      const key = String(name ?? "");
                      return [Number(value).toFixed(1), labels[key] ?? key];
                    }}
                  />
                  {/* Confidence band */}
                  <Area
                    type="monotone"
                    dataKey="upper_bound"
                    stroke="none"
                    fill="url(#confidenceFill)"
                    fillOpacity={1}
                    isAnimationActive={false}
                  />
                  <Area
                    type="monotone"
                    dataKey="lower_bound"
                    stroke="none"
                    fill="#1e293b"
                    fillOpacity={1}
                    isAnimationActive={false}
                  />
                  {/* Upper/Lower bound lines */}
                  <Line
                    type="monotone"
                    dataKey="upper_bound"
                    stroke="#3b82f6"
                    strokeWidth={1}
                    strokeDasharray="4 4"
                    strokeOpacity={0.4}
                    dot={false}
                    isAnimationActive={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="lower_bound"
                    stroke="#3b82f6"
                    strokeWidth={1}
                    strokeDasharray="4 4"
                    strokeOpacity={0.4}
                    dot={false}
                    isAnimationActive={false}
                  />
                  {/* Predicted line */}
                  <Line
                    type="monotone"
                    dataKey="predicted"
                    stroke="#3b82f6"
                    strokeWidth={2.5}
                    dot={{ r: 2.5, fill: "#3b82f6", strokeWidth: 0 }}
                    activeDot={{ r: 5, fill: "#3b82f6", stroke: "#1e293b", strokeWidth: 2 }}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[380px] flex items-center justify-center">
                <p className="text-muted-foreground text-sm">
                  No forecast data points returned.
                </p>
              </div>
            )}

            {/* Chart legend */}
            <div className="flex items-center justify-center gap-6 mt-3 text-xs text-muted-foreground">
              <div className="flex items-center gap-1.5">
                <span className="w-5 h-0.5 bg-[#3b82f6] rounded-full inline-block" />
                Predicted
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-5 h-0.5 bg-[#3b82f6]/40 rounded-full inline-block border-t border-dashed border-[#3b82f6]" />
                Confidence Bounds
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-4 h-3 bg-[#3b82f6]/10 rounded-sm inline-block" />
                Confidence Band
              </div>
            </div>
          </div>

          {/* Model Info + Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Model Info */}
            <div className="bg-card rounded-lg border border-border p-5">
              <h3 className="text-sm font-medium text-muted-foreground mb-3">
                Model Information
              </h3>
              <dl className="space-y-3">
                <div className="flex justify-between">
                  <dt className="text-sm text-muted-foreground">Model</dt>
                  <dd className="text-sm font-medium text-foreground">
                    {forecast.model_used}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-sm text-muted-foreground">Station</dt>
                  <dd className="text-sm font-medium text-foreground">
                    {forecast.station_id}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-sm text-muted-foreground">Parameter</dt>
                  <dd className="text-sm font-medium text-foreground">
                    {forecast.parameter}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-sm text-muted-foreground">Horizon</dt>
                  <dd className="text-sm font-medium text-foreground">
                    {forecast.horizon_hours} hours
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-sm text-muted-foreground">Forecast Points</dt>
                  <dd className="text-sm font-medium text-foreground">
                    {forecast.forecast.length}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-sm text-muted-foreground">Generated At</dt>
                  <dd className="text-sm font-medium text-foreground">
                    {new Date(forecast.generated_at).toLocaleString("en-IN")}
                  </dd>
                </div>
              </dl>
            </div>

            {/* Model Metrics */}
            <div className="bg-card rounded-lg border border-border p-5">
              <h3 className="text-sm font-medium text-muted-foreground mb-3">
                Model Metrics
              </h3>
              {Object.keys(forecast.model_metrics).length > 0 ? (
                <dl className="space-y-3">
                  {Object.entries(forecast.model_metrics).map(([key, value]) => (
                    <div key={key} className="flex justify-between">
                      <dt className="text-sm text-muted-foreground">
                        {formatMetricKey(key)}
                      </dt>
                      <dd className="text-sm font-mono font-medium text-foreground">
                        {formatMetricValue(value)}
                      </dd>
                    </div>
                  ))}
                </dl>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No metrics available for this model.
                </p>
              )}
            </div>
          </div>

          {/* Summary Stats */}
          {chartData.length > 0 && (
            <div className="bg-card rounded-lg border border-border p-5">
              <h3 className="text-sm font-medium text-muted-foreground mb-3">
                Forecast Summary
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {[
                  {
                    label: "Min Predicted",
                    value: Math.min(...chartData.map((d) => d.predicted)).toFixed(1),
                  },
                  {
                    label: "Max Predicted",
                    value: Math.max(...chartData.map((d) => d.predicted)).toFixed(1),
                  },
                  {
                    label: "Avg Predicted",
                    value: (
                      chartData.reduce((sum, d) => sum + d.predicted, 0) /
                      chartData.length
                    ).toFixed(1),
                  },
                  {
                    label: "Avg Confidence Width",
                    value: (
                      chartData.reduce(
                        (sum, d) => sum + (d.upper_bound - d.lower_bound),
                        0
                      ) / chartData.length
                    ).toFixed(1),
                  },
                ].map((stat) => (
                  <div
                    key={stat.label}
                    className="bg-muted/20 rounded-lg p-3 text-center"
                  >
                    <p className="text-xs text-muted-foreground">{stat.label}</p>
                    <p className="text-lg font-bold text-foreground mt-0.5">
                      {stat.value}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
