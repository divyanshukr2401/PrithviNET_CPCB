"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { getForecast, getStations } from "@/lib/api";
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
import { Activity, RefreshCw, AlertTriangle } from "lucide-react";

const PARAMETERS = ["AQI", "PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "NH3", "Pb"];
const HORIZONS = [6, 12, 24, 48, 72];

interface StationOption {
  id: string;
  label: string;
  city: string;
  state: string;
}

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

function ForecastPageInner() {
  const searchParams = useSearchParams();
  const initialStation = searchParams.get("station") || "";

  // Station list (fetched dynamically)
  const [allStations, setAllStations] = useState<StationOption[]>([]);
  const [stationsLoading, setStationsLoading] = useState(true);
  const [stationSearch, setStationSearch] = useState("");

  // Forecast config
  const [selectedStation, setSelectedStation] = useState(initialStation);
  const [selectedParam, setSelectedParam] = useState("AQI");
  const [selectedHorizon, setSelectedHorizon] = useState(24);

  // Forecast results
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);

  // Fetch stations on mount
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await getStations();
        if (!cancelled) {
          const opts: StationOption[] = data.stations.map((s) => ({
            id: s.station_id,
            label: `${s.station_name} (${s.city}, ${s.state})`,
            city: s.city,
            state: s.state,
          }));
          setAllStations(opts);
          // Use URL param station if valid, otherwise first station
          if (initialStation && opts.some((o) => o.id === initialStation)) {
            setSelectedStation(initialStation);
          } else if (opts.length > 0 && !selectedStation) {
            setSelectedStation(opts[0].id);
          }
        }
      } catch {
        // Fallback: no stations
      } finally {
        if (!cancelled) setStationsLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  const handleGenerate = async () => {
    if (!selectedStation) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getForecast({
        station_id: selectedStation,
        parameter: selectedParam,
        horizon_hours: selectedHorizon,
      });
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

  // Filter stations by search query
  const filteredStations = stationSearch.trim()
    ? allStations.filter((s) =>
        s.label.toLowerCase().includes(stationSearch.trim().toLowerCase()) ||
        s.id.toLowerCase().includes(stationSearch.trim().toLowerCase())
      )
    : allStations;

  const stationLabel =
    allStations.find((s) => s.id === selectedStation)?.label ?? selectedStation;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Activity className="w-6 h-6 text-primary" />
          Probabilistic Forecast
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Generate air quality predictions for any CPCB station across India using Nixtla TimeGPT with Holt exponential smoothing fallback.
        </p>
      </div>

      {/* Controls */}
      <div className="bg-card rounded-lg border border-border p-5">
        <h2 className="text-sm font-medium text-muted-foreground mb-4">
          Forecast Configuration
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Station selector with search */}
          <div className="sm:col-span-2">
            <label
              htmlFor="station-search"
              className="block text-xs font-medium text-muted-foreground mb-1.5"
            >
              Station ({allStations.length} available)
            </label>
            <input
              id="station-search"
              type="text"
              value={stationSearch}
              onChange={(e) => setStationSearch(e.target.value)}
              placeholder="Search stations by name, city, or ID..."
              className="w-full rounded-lg border border-border bg-card text-foreground px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 placeholder:text-muted-foreground/50 mb-2"
            />
            <select
              id="station-select"
              value={selectedStation}
              onChange={(e) => setSelectedStation(e.target.value)}
              disabled={stationsLoading}
              className="w-full rounded-lg border border-border bg-card text-foreground px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              size={1}
            >
              {stationsLoading && <option>Loading stations...</option>}
              {filteredStations.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.id} &mdash; {s.city}, {s.state}
                </option>
              ))}
            </select>
          </div>

          {/* Parameter selector */}
          <div>
            <label
              htmlFor="param-select"
              className="block text-xs font-medium text-muted-foreground mb-1.5"
            >
              Parameter
            </label>
            <select
              id="param-select"
              value={selectedParam}
              onChange={(e) => setSelectedParam(e.target.value)}
              className="w-full rounded-lg border border-border bg-card text-foreground px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
            >
              {PARAMETERS.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </div>

          {/* Horizon selector */}
          <div>
            <label
              htmlFor="horizon-select"
              className="block text-xs font-medium text-muted-foreground mb-1.5"
            >
              Horizon
            </label>
            <select
              id="horizon-select"
              value={selectedHorizon}
              onChange={(e) => setSelectedHorizon(Number(e.target.value))}
              className="w-full rounded-lg border border-border bg-card text-foreground px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
            >
              {HORIZONS.map((h) => (
                <option key={h} value={h}>{h}h</option>
              ))}
            </select>
          </div>
        </div>

        {/* Generate button */}
        <div className="mt-4">
          <button
            onClick={handleGenerate}
            disabled={loading || !selectedStation}
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
          <p className="text-red-700 font-medium text-sm">Forecast Error</p>
          <p className="text-muted-foreground text-sm mt-1">{error}</p>
        </div>
      )}

      {/* Empty State */}
      {!loading && !forecast && !error && (
        <div className="bg-card rounded-lg border border-border p-12 text-center">
          <Activity className="w-10 h-10 text-muted-foreground/40 mx-auto mb-3" />
          <p className="text-muted-foreground text-sm">
            Select a station, parameter, and horizon, then click <span className="text-foreground font-medium">Generate Forecast</span> to view predictions with confidence intervals.
          </p>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="bg-card rounded-lg border border-border p-12 text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-primary mx-auto mb-3" />
          <p className="text-muted-foreground text-sm">
            Generating {selectedParam} forecast for {selectedHorizon}h...
          </p>
        </div>
      )}

      {/* Forecast Results */}
      {forecast && !loading && (() => {
        const isInsufficientData =
          forecast.model_metrics?.warning === "insufficient_data";

        return (
        <div className="space-y-6">
          {/* Insufficient Data Warning */}
          {isInsufficientData && (
            <div className="bg-amber-50 rounded-lg border border-amber-300 p-5">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
                <div>
                  <h3 className="font-medium text-amber-800">
                    Insufficient Historical Data
                  </h3>
                  <p className="text-sm text-amber-700 mt-1">
                    Station <span className="font-semibold">{stationLabel}</span> does
                    not have enough historical <span className="font-semibold">{forecast.parameter}</span> readings
                    to generate a meaningful forecast. At least 24 hourly data points
                    are required for the forecasting model to produce reliable predictions.
                  </p>
                  <p className="text-xs text-amber-600 mt-2">
                    Try selecting a different station or parameter that has more data available in the system.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Chart — only render when we have real data */}
          {!isInsufficientData && (
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
                  <CartesianGrid strokeDasharray="3 3" stroke="#d1d5db" />
                  <XAxis
                    dataKey="label"
                    tick={{ fill: "#5a6570", fontSize: 11 }}
                    tickLine={{ stroke: "#d1d5db" }}
                    axisLine={{ stroke: "#d1d5db" }}
                    interval="preserveStartEnd"
                    angle={-30}
                    textAnchor="end"
                    height={60}
                  />
                  <YAxis
                    tick={{ fill: "#5a6570", fontSize: 11 }}
                    tickLine={{ stroke: "#d1d5db" }}
                    axisLine={{ stroke: "#d1d5db" }}
                    label={{
                      value: forecast.parameter,
                      angle: -90,
                      position: "insideLeft",
                      fill: "#5a6570",
                      fontSize: 12,
                    }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#ffffff",
                      border: "1px solid #d1d5db",
                      borderRadius: "8px",
                      color: "#1a1a2e",
                      fontSize: "12px",
                    }}
                    labelStyle={{ color: "#5a6570", marginBottom: "4px" }}
                    formatter={(value: unknown, name: unknown) => {
                      const labels: Record<string, string> = {
                        predicted: "Predicted",
                        upper_bound: "Upper Bound (90%)",
                        lower_bound: "Lower Bound (90%)",
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
                    fill="#ffffff"
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
                    activeDot={{ r: 5, fill: "#3b82f6", stroke: "#ffffff", strokeWidth: 2 }}
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
                90% Confidence Bounds
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-4 h-3 bg-[#3b82f6]/10 rounded-sm inline-block" />
                Confidence Band
              </div>
            </div>
          </div>
          )}

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

          {/* Summary Stats — only when real data exists */}
          {!isInsufficientData && chartData.length > 0 && (
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
        );
      })()}
    </div>
  );
}

export default function ForecastPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center py-24 text-muted-foreground text-sm gap-2">
        <RefreshCw className="w-4 h-4 animate-spin" />
        Loading forecast...
      </div>
    }>
      <ForecastPageInner />
    </Suspense>
  );
}
