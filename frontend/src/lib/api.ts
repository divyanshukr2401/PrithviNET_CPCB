// PRITHVINET API Client
// Maps backend responses to frontend types

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8005";

async function fetchAPI<T>(path: string, options?: RequestInit & { timeoutMs?: number }): Promise<T> {
  const { timeoutMs, ...fetchOptions } = options || {};
  const timeout = timeoutMs ?? 60_000; // default 60s timeout

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...fetchOptions,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...fetchOptions?.headers,
      },
    });
    if (!res.ok) {
      throw new Error(`API error: ${res.status} ${res.statusText}`);
    }
    return res.json();
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error(`Request timed out after ${Math.round(timeout / 1000)}s`);
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

// ── Health ─────────────────────────────────────────────────
import type {
  HealthResponse,
  LiveResponse,
  ForecastResponse,
  WhatIfResponse,
  CausalDAGResponse,
  AutoHealerDiagnosis,
  LeaderboardEntry,
  Factory,
  WaterQualityHeatmapResponse,
  GroundwaterResponse,
  YearlyForecastResponse,
} from "./types";

export async function getHealth(): Promise<HealthResponse> {
  return fetchAPI("/health");
}

// ── Air Quality ────────────────────────────────────────────
export async function getLiveAir(params?: {
  station_id?: string;
  city?: string;
  include_pollutants?: boolean;
}): Promise<LiveResponse> {
  const sp = new URLSearchParams();
  if (params?.station_id) sp.set("station_id", params.station_id);
  if (params?.city) sp.set("city", params.city);
  if (params?.include_pollutants) sp.set("include_pollutants", "true");
  const qs = sp.toString();
  return fetchAPI(`/api/v1/air/live${qs ? `?${qs}` : ""}`);
}

export async function getStations(): Promise<{
  stations: Array<{
    station_id: string;
    station_name: string;
    city: string;
    state: string;
    latitude: number;
    longitude: number;
  }>;
}> {
  return fetchAPI("/api/v1/air/stations?limit=1000");
}

export async function getHistoricalAir(params: {
  station_id: string;
  parameter?: string;
  days?: number;
}): Promise<{
  station_id: string;
  parameter: string;
  days: number;
  data_points: number;
  data: Array<{ timestamp: string; value: number; parameter: string }>;
  statistics: Record<string, number>;
}> {
  const sp = new URLSearchParams();
  sp.set("station_id", params.station_id);
  if (params.parameter) sp.set("parameter", params.parameter);
  if (params.days) sp.set("days", String(params.days));
  return fetchAPI(`/api/v1/air/historical?${sp.toString()}`);
}

// ── Forecasting ────────────────────────────────────────────
// Backend returns: { station_id, parameter, model_name, created_at, horizon_hours,
//   forecasts: [{ target_time, predicted_mean, predicted_lo90, predicted_hi90, ... }], model_metrics }
// Frontend expects: { station_id, parameter, model_used, horizon_hours, generated_at,
//   forecast: [{ timestamp, predicted, lower_bound, upper_bound }], model_metrics }
interface BackendForecastPoint {
  target_time: string;
  predicted_mean: number;
  predicted_lo90: number;
  predicted_hi90: number;
  predicted_lo50: number;
  predicted_hi50: number;
}

interface BackendForecastResponse {
  station_id: string;
  parameter: string;
  model_name: string;
  created_at: string;
  horizon_hours: number;
  forecasts: BackendForecastPoint[];
  model_metrics: Record<string, unknown>;
}

export async function getForecast(params: {
  station_id: string;
  parameter?: string;
  horizon_hours?: number;
}): Promise<ForecastResponse> {
  const sp = new URLSearchParams();
  sp.set("station_id", params.station_id);
  sp.set("parameter", params.parameter || "AQI");
  sp.set("horizon_hours", String(params.horizon_hours || 24));
  const raw = await fetchAPI<BackendForecastResponse>(
    `/api/v1/forecast/air-quality?${sp.toString()}`,
    { method: "POST" }
  );
  // Transform backend shape → frontend shape
  return {
    station_id: raw.station_id,
    parameter: raw.parameter,
    model_used: raw.model_name,
    horizon_hours: raw.horizon_hours,
    generated_at: raw.created_at,
    forecast: raw.forecasts.map((pt) => ({
      timestamp: pt.target_time,
      predicted: pt.predicted_mean,
      lower_bound: pt.predicted_lo90,
      upper_bound: pt.predicted_hi90,
    })),
    model_metrics: raw.model_metrics,
  };
}

// ── Causal ─────────────────────────────────────────────────
export async function getCausalDAG(): Promise<CausalDAGResponse> {
  return fetchAPI("/api/v1/causal/dag");
}

export async function runWhatIf(params?: {
  city?: string;
  target_parameter?: string;
}): Promise<WhatIfResponse> {
  const sp = new URLSearchParams();
  if (params?.city) sp.set("city", params.city);
  if (params?.target_parameter)
    sp.set("target_parameter", params.target_parameter);
  const qs = sp.toString();
  return fetchAPI(`/api/v1/causal/what-if${qs ? `?${qs}` : ""}`, {
    method: "POST",
  });
}

// ── Compliance / OCEMS ─────────────────────────────────────
export async function getFactories(params?: {
  city?: string;
  risk?: string;
}): Promise<{ factories: Factory[]; total: number }> {
  const sp = new URLSearchParams();
  if (params?.city) sp.set("city", params.city);
  if (params?.risk) sp.set("risk", params.risk);
  const qs = sp.toString();
  return fetchAPI(`/api/v1/compliance/factories${qs ? `?${qs}` : ""}`);
}

export async function diagnoseFactory(
  factoryId: string,
  params?: { parameter?: string; hours?: number }
): Promise<AutoHealerDiagnosis> {
  const sp = new URLSearchParams();
  if (params?.parameter) sp.set("parameter", params.parameter);
  if (params?.hours) sp.set("hours", String(params.hours));
  const qs = sp.toString();
  // Backend endpoint is GET, not POST
  return fetchAPI(
    `/api/v1/compliance/auto-healer/diagnose/${factoryId}${qs ? `?${qs}` : ""}`
  );
}

export async function getComplianceSummary(): Promise<{
  total_factories: number;
  monitored_24h: number;
  compliant: number;
  non_compliant: number;
  critical: number;
  overall_compliance_pct: number;
  last_updated: string;
}> {
  return fetchAPI("/api/v1/compliance/");
}

export async function getExceedances(params?: {
  hours?: number;
}): Promise<{
  exceedances: Array<{
    factory_id: string;
    parameter: string;
    city: string;
    industry_type: string;
    value: number;
    limit: number;
    exceedance_pct: number;
    timestamp: string;
    anomaly_type: string;
    quality_flag: string;
  }>;
}> {
  const sp = new URLSearchParams();
  if (params?.hours) sp.set("hours", String(params.hours));
  const qs = sp.toString();
  return fetchAPI(`/api/v1/compliance/exceedances${qs ? `?${qs}` : ""}`);
}

// ── Gamification ───────────────────────────────────────────
// Backend returns array directly, not { leaderboard: [...] }
export async function getLeaderboard(): Promise<LeaderboardEntry[]> {
  return fetchAPI("/api/v1/gamification/leaderboard");
}

export async function getGamificationUser(
  userId: string
): Promise<{ user_id: string; username: string; city: string; eco_points: number; level: number; badges: string[]; rank: number | null }> {
  return fetchAPI(`/api/v1/gamification/user/${userId}`);
}

export async function submitReport(report: {
  user_id: string;
  report_type: string;
  description: string;
  latitude: number;
  longitude: number;
  severity?: string;
}): Promise<{ status: string; report_id: string; points_awarded: number }> {
  return fetchAPI("/api/v1/gamification/report", {
    method: "POST",
    body: JSON.stringify(report),
  });
}

// ── Water Quality Heatmap ─────────────────────────────────
export async function getWaterQualityHeatmap(params?: {
  limit?: number;
  state?: string;
}): Promise<WaterQualityHeatmapResponse> {
  const sp = new URLSearchParams();
  if (params?.limit) sp.set("limit", String(params.limit));
  if (params?.state) sp.set("state", params.state);
  const qs = sp.toString();
  return fetchAPI(`/api/v1/water/quality-heatmap${qs ? `?${qs}` : ""}`, {
    timeoutMs: 90_000, // water quality fetch can take up to 90s on cold cache
  });
}

// ── Groundwater Level ─────────────────────────────────────
export async function getGroundwaterLevel(params?: {
  city?: string;
}): Promise<GroundwaterResponse> {
  const sp = new URLSearchParams();
  if (params?.city) sp.set("city", params.city);
  const qs = sp.toString();
  return fetchAPI(`/api/v1/water/groundwater-level${qs ? `?${qs}` : ""}`);
}

// ── Yearly AQI Forecast ──────────────────────────────────
export async function getYearlyForecast(stationId: string): Promise<YearlyForecastResponse> {
  return fetchAPI(`/api/v1/forecast/yearly-profile?station_id=${encodeURIComponent(stationId)}`);
}

// ── Noise Monitoring ─────────────────────────────────────
import type { NoiseLiveResponse, NoiseHistoricalResponse } from "./types";

export async function getNoiseLive(): Promise<NoiseLiveResponse> {
  return fetchAPI("/api/v1/noise/live");
}

export async function getNoiseHistorical(
  stationId: string,
  hours: number = 24
): Promise<NoiseHistoricalResponse> {
  return fetchAPI(
    `/api/v1/noise/historical/${encodeURIComponent(stationId)}?hours=${hours}`
  );
}

export async function getNoiseStandards(): Promise<{
  standards: Record<string, { day_limit: number; night_limit: number; unit: string }>;
  day_hours: string;
  night_hours: string;
  reference: string;
}> {
  return fetchAPI("/api/v1/noise/standards");
}

// ── AI Copilot ───────────────────────────────────────────────
export interface CopilotMessage {
  role: "user" | "assistant";
  content: string;
}

export interface CopilotResponse {
  response: string;
  mode: string;
  context_summary?: string;
}

export async function sendCopilotMessage(params: {
  message: string;
  active_layer?: string;
  history?: CopilotMessage[];
  mode?: string;
}): Promise<CopilotResponse> {
  return fetchAPI("/api/v1/copilot/chat", {
    method: "POST",
    body: JSON.stringify({
      message: params.message,
      active_layer: params.active_layer || null,
      history: params.history?.map((m) => ({
        role: m.role === "assistant" ? "assistant" : "user",
        content: m.content,
      })),
      mode: params.mode || "analyst",
    }),
  });
}

export async function getCopilotSuggestions(
  activeLayer?: string
): Promise<{ suggestions: string[] }> {
  const qs = activeLayer ? `?active_layer=${activeLayer}` : "";
  return fetchAPI(`/api/v1/copilot/suggestions${qs}`);
}

// ── Report Generation ────────────────────────────────────────
export interface ReportParams {
  include_aqi?: boolean;
  include_water?: boolean;
  include_noise?: boolean;
}

function _buildReportQS(params?: ReportParams): string {
  if (!params) return "";
  const sp = new URLSearchParams();
  if (params.include_aqi === false) sp.set("include_aqi", "false");
  if (params.include_water === false) sp.set("include_water", "false");
  if (params.include_noise === false) sp.set("include_noise", "false");
  const qs = sp.toString();
  return qs ? `&${qs}` : "";
}

export async function downloadCityReport(
  city: string,
  params?: ReportParams
): Promise<Blob> {
  const qs = _buildReportQS(params);
  const res = await fetch(
    `${API_BASE}/api/v1/report/city?city=${encodeURIComponent(city)}${qs}`
  );
  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error");
    throw new Error(`Report generation failed (${res.status}): ${text}`);
  }
  return res.blob();
}

export async function downloadStateReport(
  state: string,
  params?: ReportParams
): Promise<Blob> {
  const qs = _buildReportQS(params);
  const res = await fetch(
    `${API_BASE}/api/v1/report/state?state=${encodeURIComponent(state)}${qs}`
  );
  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error");
    throw new Error(`Report generation failed (${res.status}): ${text}`);
  }
  return res.blob();
}

export async function downloadNationalReport(
  params?: ReportParams
): Promise<Blob> {
  const sp = new URLSearchParams();
  if (params?.include_aqi === false) sp.set("include_aqi", "false");
  if (params?.include_water === false) sp.set("include_water", "false");
  if (params?.include_noise === false) sp.set("include_noise", "false");
  const qs = sp.toString();
  const res = await fetch(
    `${API_BASE}/api/v1/report/national${qs ? `?${qs}` : ""}`
  );
  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error");
    throw new Error(`Report generation failed (${res.status}): ${text}`);
  }
  return res.blob();
}

export async function getAvailableCities(): Promise<{
  cities: string[];
  count: number;
}> {
  return fetchAPI("/api/v1/report/available-cities");
}

export async function getAvailableStates(): Promise<{
  states: string[];
  count: number;
}> {
  return fetchAPI("/api/v1/report/available-states");
}
