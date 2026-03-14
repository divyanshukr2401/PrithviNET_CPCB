"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { getYearlyForecast, getStations } from "@/lib/api";
import type { YearlyForecastResponse, MonthlySummary } from "@/lib/types";
import {
  getAQICategory,
  getAQIColor,
  CPCB_AQI_COLORS,
  AQI_CATEGORIES_ORDERED,
  CPCB_AQI_RANGES,
} from "@/lib/types";
import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceArea,
  ReferenceLine,
} from "recharts";
import { Activity, RefreshCw, TrendingUp, TrendingDown, BarChart3, Calendar } from "lucide-react";

// ── CPCB AQI band definitions for chart background ─────────
const AQI_BANDS = [
  { y1: 0, y2: 50, color: CPCB_AQI_COLORS.Good, label: "Good" },
  { y1: 50, y2: 100, color: CPCB_AQI_COLORS.Satisfactory, label: "Satisfactory" },
  { y1: 100, y2: 200, color: CPCB_AQI_COLORS.Moderate, label: "Moderate" },
  { y1: 200, y2: 300, color: CPCB_AQI_COLORS.Poor, label: "Poor" },
  { y1: 300, y2: 400, color: CPCB_AQI_COLORS["Very Poor"], label: "Very Poor" },
  { y1: 400, y2: 500, color: CPCB_AQI_COLORS.Severe, label: "Severe" },
];

interface StationOption {
  id: string;
  label: string;
  city: string;
  state: string;
}

// Unified chart data point: merges historical + forecast into one array
interface ChartPoint {
  date: string;         // "2025-04-01"
  dateLabel: string;    // "Apr 01"
  // Historical fields (null when in forecast zone)
  hist_avg: number | null;
  hist_min: number | null;
  hist_max: number | null;
  // Forecast fields (null when in historical zone)
  fc_predicted: number | null;
  fc_lower: number | null;
  fc_upper: number | null;
}

function formatMonth(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString("en-IN", { month: "short", day: "2-digit" });
}

function formatMonthYear(monthStr: string): string {
  const [y, m] = monthStr.split("-");
  const d = new Date(Number(y), Number(m) - 1, 1);
  return d.toLocaleDateString("en-IN", { month: "short", year: "2-digit" });
}

// ── Custom Tooltip — reads data point directly so forecast values always show ──
function ChartTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: ChartPoint }> }) {
  if (!active || !payload?.length) return null;
  const point = payload[0]?.payload;
  if (!point) return null;

  const isHistorical = point.hist_avg !== null;
  const isForecast = point.fc_predicted !== null;

  return (
    <div className="bg-white border border-gray-200 rounded-lg px-3 py-2 shadow-md text-xs min-w-[140px]">
      <p className="text-gray-500 mb-1.5 font-semibold">{point.dateLabel}</p>
      {isHistorical && (
        <div className="space-y-0.5">
          <p style={{ color: "#2563eb" }}>Average AQI : {Math.round(point.hist_avg!)}</p>
          <p className="text-gray-400">Min AQI : {Math.round(point.hist_min!)}</p>
          <p className="text-orange-500">Max AQI : {Math.round(point.hist_max!)}</p>
        </div>
      )}
      {isForecast && (
        <div className={isHistorical ? "mt-1.5 pt-1.5 border-t border-gray-100 space-y-0.5" : "space-y-0.5"}>
          <p style={{ color: "#d97706" }} className="font-medium">Predicted AQI : {Math.round(point.fc_predicted!)}</p>
          <p className="text-gray-400">Lower : {Math.round(point.fc_lower!)}</p>
          <p className="text-gray-400">Upper : {Math.round(point.fc_upper!)}</p>
        </div>
      )}
    </div>
  );
}

function ForecastPageInner() {
  const searchParams = useSearchParams();
  const initialStation = searchParams.get("station") || "";

  // Station list
  const [allStations, setAllStations] = useState<StationOption[]>([]);
  const [stationsLoading, setStationsLoading] = useState(true);
  const [stationSearch, setStationSearch] = useState("");

  // Forecast state
  const [selectedStation, setSelectedStation] = useState(initialStation);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<YearlyForecastResponse | null>(null);

  // Fetch stations on mount
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await getStations();
        if (!cancelled) {
          const opts: StationOption[] = res.stations.map((s) => ({
            id: s.station_id,
            label: `${s.station_name} (${s.city}, ${s.state})`,
            city: s.city,
            state: s.state,
          }));
          setAllStations(opts);
          if (initialStation && opts.some((o) => o.id === initialStation)) {
            setSelectedStation(initialStation);
          } else if (opts.length > 0 && !selectedStation) {
            setSelectedStation(opts[0].id);
          }
        }
      } catch {
        // ignore
      } finally {
        if (!cancelled) setStationsLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  // Auto-fetch when station changes
  useEffect(() => {
    if (!selectedStation) return;
    let cancelled = false;
    async function fetch() {
      setLoading(true);
      setError(null);
      try {
        const result = await getYearlyForecast(selectedStation);
        if (!cancelled) setData(result);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load yearly forecast");
          setData(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetch();
    return () => { cancelled = true; };
  }, [selectedStation]);

  // ── Build unified chart data ──────────────────────────────────────
  const chartData: ChartPoint[] = [];
  const todayStr = data?.historical?.length
    ? data.historical[data.historical.length - 1].date
    : new Date().toISOString().slice(0, 10);

  if (data) {
    // Historical points
    for (const pt of data.historical) {
      chartData.push({
        date: pt.date,
        dateLabel: formatMonth(pt.date),
        hist_avg: pt.avg_aqi,
        hist_min: pt.min_aqi,
        hist_max: pt.max_aqi,
        fc_predicted: null,
        fc_lower: null,
        fc_upper: null,
      });
    }
    // Bridge point: last historical = first forecast anchor
    if (data.historical.length > 0 && data.forecast.length > 0) {
      const lastHist = data.historical[data.historical.length - 1];
      chartData.push({
        date: lastHist.date,
        dateLabel: formatMonth(lastHist.date),
        hist_avg: lastHist.avg_aqi,
        hist_min: lastHist.min_aqi,
        hist_max: lastHist.max_aqi,
        fc_predicted: lastHist.avg_aqi,
        fc_lower: lastHist.min_aqi,
        fc_upper: lastHist.max_aqi,
      });
    }
    // Forecast points
    for (const pt of data.forecast) {
      chartData.push({
        date: pt.date,
        dateLabel: formatMonth(pt.date),
        hist_avg: null,
        hist_min: null,
        hist_max: null,
        fc_predicted: pt.predicted,
        fc_lower: pt.lower,
        fc_upper: pt.upper,
      });
    }
  }

  // ── Compute stats from monthly summary ───────────────────────────
  const histMonths = data?.monthly_summary?.filter((m) => !m.is_forecast) ?? [];
  const fcMonths = data?.monthly_summary?.filter((m) => m.is_forecast) ?? [];

  const worstHistMonth = histMonths.length
    ? histMonths.reduce((a, b) => (a.avg_aqi > b.avg_aqi ? a : b))
    : null;
  const bestHistMonth = histMonths.length
    ? histMonths.reduce((a, b) => (a.avg_aqi < b.avg_aqi ? a : b))
    : null;
  const worstFcMonth = fcMonths.length
    ? fcMonths.reduce((a, b) => (a.avg_aqi > b.avg_aqi ? a : b))
    : null;
  const annualAvg = histMonths.length
    ? Math.round(histMonths.reduce((s, m) => s + m.avg_aqi, 0) / histMonths.length)
    : null;

  // Filter stations by search
  const filteredStations = stationSearch.trim()
    ? allStations.filter(
        (s) =>
          s.label.toLowerCase().includes(stationSearch.trim().toLowerCase()) ||
          s.id.toLowerCase().includes(stationSearch.trim().toLowerCase())
      )
    : allStations;

  const stationLabel =
    allStations.find((s) => s.id === selectedStation)?.label ?? selectedStation;

  // ── Determine Y-axis max from data ────────────────────────────────
  let yMax = 500;
  if (chartData.length > 0) {
    const allVals = chartData.flatMap((p) =>
      [p.hist_max, p.fc_upper, p.hist_avg, p.fc_predicted].filter(
        (v): v is number => v !== null
      )
    );
    if (allVals.length > 0) {
      const dataMax = Math.max(...allVals);
      // Round up to next AQI band boundary
      if (dataMax <= 50) yMax = 100;
      else if (dataMax <= 100) yMax = 150;
      else if (dataMax <= 200) yMax = 300;
      else if (dataMax <= 300) yMax = 400;
      else if (dataMax <= 400) yMax = 500;
      else yMax = 500;
    }
  }

  // ── Thin out X-axis ticks for readability ─────────────────────────
  // Show ~18 ticks (roughly 1 per month)
  const tickInterval = Math.max(1, Math.floor(chartData.length / 18));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2 text-foreground">
          <Calendar className="w-6 h-6 text-primary" />
          Yearly AQI Forecast
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          12-month historical AQI trend with 6-month seasonal forecast. CPCB National AQI color bands indicate air quality categories.
        </p>
      </div>

      {/* Station Selector */}
      <div className="bg-card rounded-lg border border-border p-5">
        <h2 className="text-sm font-medium text-muted-foreground mb-3">
          Select Station
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="sm:col-span-2">
            <input
              type="text"
              value={stationSearch}
              onChange={(e) => setStationSearch(e.target.value)}
              placeholder="Search stations by name, city, or ID..."
              className="w-full rounded-lg border border-border bg-card text-foreground px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 placeholder:text-muted-foreground/50 mb-2"
            />
            <select
              value={selectedStation}
              onChange={(e) => setSelectedStation(e.target.value)}
              disabled={stationsLoading}
              className="w-full rounded-lg border border-border bg-card text-foreground px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
            >
              {stationsLoading && <option>Loading stations...</option>}
              {filteredStations.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.id} &mdash; {s.city}, {s.state}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-card rounded-lg border border-red-500/30 p-5">
          <p className="text-red-700 font-medium text-sm">Forecast Error</p>
          <p className="text-muted-foreground text-sm mt-1">{error}</p>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="bg-card rounded-lg border border-border p-12 text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-primary mx-auto mb-3" />
          <p className="text-muted-foreground text-sm">
            Loading yearly AQI profile for {stationLabel}...
          </p>
        </div>
      )}

      {/* Empty */}
      {!loading && !data && !error && (
        <div className="bg-card rounded-lg border border-border p-12 text-center">
          <Activity className="w-10 h-10 text-muted-foreground/40 mx-auto mb-3" />
          <p className="text-muted-foreground text-sm">
            Select a station above to view its yearly AQI forecast.
          </p>
        </div>
      )}

      {/* Results */}
      {data && !loading && (
        <div className="space-y-6">
          {/* Stats Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              {
                label: "Annual Average",
                value: annualAvg !== null ? String(annualAvg) : "—",
                sub: annualAvg !== null ? getAQICategory(annualAvg) : "",
                color: annualAvg !== null ? getAQIColor(annualAvg) : "#6b7280",
                icon: BarChart3,
              },
              {
                label: "Best Month (Historical)",
                value: bestHistMonth ? String(Math.round(bestHistMonth.avg_aqi)) : "—",
                sub: bestHistMonth ? formatMonthYear(bestHistMonth.month) : "",
                color: bestHistMonth ? getAQIColor(bestHistMonth.avg_aqi) : "#6b7280",
                icon: TrendingDown,
              },
              {
                label: "Worst Month (Historical)",
                value: worstHistMonth ? String(Math.round(worstHistMonth.avg_aqi)) : "—",
                sub: worstHistMonth ? formatMonthYear(worstHistMonth.month) : "",
                color: worstHistMonth ? getAQIColor(worstHistMonth.avg_aqi) : "#6b7280",
                icon: TrendingUp,
              },
              {
                label: "Predicted Worst Month",
                value: worstFcMonth ? String(Math.round(worstFcMonth.avg_aqi)) : "—",
                sub: worstFcMonth ? formatMonthYear(worstFcMonth.month) : "",
                color: worstFcMonth ? getAQIColor(worstFcMonth.avg_aqi) : "#6b7280",
                icon: Activity,
              },
            ].map((card) => (
              <div
                key={card.label}
                className="bg-card rounded-lg border border-border p-4"
              >
                <div className="flex items-center gap-2 mb-2">
                  <card.icon className="w-4 h-4 text-muted-foreground" />
                  <p className="text-xs text-muted-foreground">{card.label}</p>
                </div>
                <p className="text-2xl font-bold" style={{ color: card.color }}>
                  {card.value}
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">{card.sub}</p>
              </div>
            ))}
          </div>

          {/* Main Chart */}
          {chartData.length > 0 && (
            <div className="bg-card rounded-lg border border-border p-5">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="font-medium text-foreground">
                    AQI Yearly Profile &mdash; {data.city}
                  </h3>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {data.station_id} | {data.historical.length} days historical + {data.forecast.length} days forecast
                  </p>
                </div>
                <span className="text-xs bg-primary/10 text-primary px-2.5 py-1 rounded-full font-medium">
                  Seasonal Model
                </span>
              </div>

              <ResponsiveContainer width="100%" height={420}>
                <ComposedChart
                  data={chartData}
                  margin={{ top: 10, right: 20, left: 10, bottom: 10 }}
                >
                  {/* CPCB AQI color bands as background */}
                  {AQI_BANDS.filter((b) => b.y1 < yMax).map((band) => (
                    <ReferenceArea
                      key={band.label}
                      y1={band.y1}
                      y2={Math.min(band.y2, yMax)}
                      fill={band.color}
                      fillOpacity={0.12}
                      stroke="none"
                    />
                  ))}

                  <CartesianGrid strokeDasharray="3 3" stroke="#d1d5db" strokeOpacity={0.5} />

                  <XAxis
                    dataKey="dateLabel"
                    tick={{ fill: "#5a6570", fontSize: 10 }}
                    tickLine={{ stroke: "#d1d5db" }}
                    axisLine={{ stroke: "#d1d5db" }}
                    interval={tickInterval}
                    angle={-35}
                    textAnchor="end"
                    height={55}
                  />
                  <YAxis
                    domain={[0, yMax]}
                    tick={{ fill: "#5a6570", fontSize: 11 }}
                    tickLine={{ stroke: "#d1d5db" }}
                    axisLine={{ stroke: "#d1d5db" }}
                    label={{
                      value: "AQI",
                      angle: -90,
                      position: "insideLeft",
                      fill: "#5a6570",
                      fontSize: 12,
                    }}
                  />

                  {/* "Today" divider line */}
                  <ReferenceLine
                    x={formatMonth(todayStr)}
                    stroke="#374151"
                    strokeWidth={2}
                    strokeDasharray="6 4"
                    label={{
                      value: "Today",
                      position: "top",
                      fill: "#374151",
                      fontSize: 11,
                      fontWeight: 600,
                    }}
                  />

                  <Tooltip
                    content={<ChartTooltip />}
                    cursor={{ stroke: "#9ca3af", strokeWidth: 1 }}
                  />

                  {/* Historical min-max range (shaded area) */}
                  <defs>
                    <linearGradient id="histRangeFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.15} />
                      <stop offset="100%" stopColor="#3b82f6" stopOpacity={0.03} />
                    </linearGradient>
                    <linearGradient id="fcRangeFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.18} />
                      <stop offset="100%" stopColor="#f59e0b" stopOpacity={0.03} />
                    </linearGradient>
                  </defs>

                  {/* Historical max area (upper bound of shaded region) */}
                  <Area
                    type="monotone"
                    dataKey="hist_max"
                    stroke="none"
                    fill="url(#histRangeFill)"
                    fillOpacity={1}
                    isAnimationActive={false}
                    connectNulls={false}
                  />
                  {/* Historical min area (carves out the bottom) */}
                  <Area
                    type="monotone"
                    dataKey="hist_min"
                    stroke="none"
                    fill="#ffffff"
                    fillOpacity={1}
                    isAnimationActive={false}
                    connectNulls={false}
                  />

                  {/* Forecast confidence band */}
                  <Area
                    type="monotone"
                    dataKey="fc_upper"
                    stroke="none"
                    fill="url(#fcRangeFill)"
                    fillOpacity={1}
                    isAnimationActive={false}
                    connectNulls={false}
                  />
                  <Area
                    type="monotone"
                    dataKey="fc_lower"
                    stroke="none"
                    fill="#ffffff"
                    fillOpacity={1}
                    isAnimationActive={false}
                    connectNulls={false}
                  />

                  {/* Historical average line (solid blue) */}
                  <Line
                    type="monotone"
                    dataKey="hist_avg"
                    stroke="#2563eb"
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                    connectNulls={false}
                  />

                  {/* Forecast predicted line (dashed amber) */}
                  <Line
                    type="monotone"
                    dataKey="fc_predicted"
                    stroke="#d97706"
                    strokeWidth={2}
                    strokeDasharray="6 3"
                    dot={false}
                    isAnimationActive={false}
                    connectNulls={false}
                  />
                </ComposedChart>
              </ResponsiveContainer>

              {/* Chart legend */}
              <div className="flex flex-wrap items-center justify-center gap-5 mt-3 text-xs text-muted-foreground">
                <div className="flex items-center gap-1.5">
                  <span className="w-5 h-0.5 bg-[#2563eb] rounded-full inline-block" />
                  Historical Avg AQI
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-4 h-3 bg-[#3b82f6]/15 rounded-sm inline-block" />
                  Min-Max Range
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-5 h-0.5 rounded-full inline-block border-t-2 border-dashed border-[#d97706]" />
                  Forecast Predicted
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-4 h-3 bg-[#f59e0b]/15 rounded-sm inline-block" />
                  Confidence Band
                </div>
              </div>
            </div>
          )}

          {/* Monthly Summary Strip */}
          {data.monthly_summary.length > 0 && (
            <div className="bg-card rounded-lg border border-border p-5">
              <h3 className="text-sm font-medium text-muted-foreground mb-3">
                Monthly AQI Summary
              </h3>
              <div className="flex gap-1 overflow-x-auto pb-1">
                {data.monthly_summary.map((m) => {
                  const bgColor = getAQIColor(m.avg_aqi);
                  // Determine text color for contrast
                  const cat = m.category;
                  const textWhite = cat === "Good" || cat === "Poor" || cat === "Very Poor" || cat === "Severe";
                  return (
                    <div
                      key={m.month}
                      className="flex-shrink-0 rounded-md px-2.5 py-2 text-center min-w-[68px] relative"
                      style={{
                        backgroundColor: bgColor,
                        color: textWhite ? "#ffffff" : "#1a1a1a",
                      }}
                    >
                      <p className="text-[10px] font-medium opacity-80">
                        {formatMonthYear(m.month)}
                      </p>
                      <p className="text-sm font-bold">{Math.round(m.avg_aqi)}</p>
                      <p className="text-[9px] opacity-70">{m.category}</p>
                      {m.is_forecast && (
                        <div
                          className="absolute top-0.5 right-0.5 w-1.5 h-1.5 rounded-full"
                          style={{ backgroundColor: textWhite ? "rgba(255,255,255,0.6)" : "rgba(0,0,0,0.3)" }}
                          title="Forecast"
                        />
                      )}
                    </div>
                  );
                })}
              </div>
              <div className="flex items-center gap-3 mt-2 text-[10px] text-muted-foreground">
                <span>Solid = Historical</span>
                <span className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-gray-400 inline-block" />
                  = Forecast
                </span>
              </div>
            </div>
          )}

          {/* AQI Legend */}
          <div className="bg-card rounded-lg border border-border p-5">
            <h3 className="text-sm font-medium text-muted-foreground mb-3">
              CPCB National AQI Categories
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
              {AQI_CATEGORIES_ORDERED.map((cat) => {
                const color = CPCB_AQI_COLORS[cat];
                const textWhite = cat === "Good" || cat === "Poor" || cat === "Very Poor" || cat === "Severe";
                return (
                  <div
                    key={cat}
                    className="rounded-md px-3 py-2 text-center"
                    style={{
                      backgroundColor: color,
                      color: textWhite ? "#ffffff" : "#1a1a1a",
                    }}
                  >
                    <p className="text-xs font-semibold">{cat}</p>
                    <p className="text-[10px] opacity-80">{CPCB_AQI_RANGES[cat]}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ForecastPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center py-24 text-muted-foreground text-sm gap-2">
          <RefreshCw className="w-4 h-4 animate-spin" />
          Loading forecast...
        </div>
      }
    >
      <ForecastPageInner />
    </Suspense>
  );
}
