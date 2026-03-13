// PRITHVINET API Types

export interface AirReading {
  station_id: string;
  timestamp: string;
  parameter: string;
  value: number;
  unit: string;
  aqi: number;
  city: string;
  latitude: number;
  longitude: number;
  zone: string;
  is_anomaly: number;
  anomaly_type: string;
  quality_flag: string;
  category?: string;
}

export interface LiveResponse {
  source: string;
  simulator_status: string;
  total_stations: number;
  readings_count: number;
  filter: {
    station_id: string | null;
    city: string | null;
    include_pollutants: boolean;
  };
  readings: AirReading[];
}

export interface HealthResponse {
  status: string;
  service: string;
  components: {
    postgres: string;
    clickhouse: string;
  };
}

export interface Station {
  station_id: string;
  station_name: string;
  city: string;
  state: string;
  latitude: number;
  longitude: number;
  station_type: string;
  operator: string;
}

export interface ForecastRequest {
  station_id: string;
  parameter?: string;
  horizon_hours?: number;
}

export interface ForecastPoint {
  timestamp: string;
  predicted: number;
  lower_bound: number;
  upper_bound: number;
}

export interface ForecastResponse {
  station_id: string;
  parameter: string;
  model_used: string;
  horizon_hours: number;
  generated_at: string;
  forecast: ForecastPoint[];
  model_metrics: Record<string, unknown>;
}

// ── Causal / What-If ───────────────────────────────────────
// Backend /causal/what-if returns scenario-based comparisons
export interface WhatIfScenario {
  scenario: string;
  intervention_type: string;
  reduction_pct_applied: number;
  baseline_value: number;
  counterfactual_value: number;
  absolute_change: number;
  relative_change_pct: number;
  confidence_interval: [number, number];
  p_value: number;
}

export interface WhatIfResponse {
  city: string;
  target_parameter: string;
  scenarios: WhatIfScenario[];
  recommendation: {
    optimal_intervention: string;
    expected_change: number;
    rationale: string;
  };
}

export interface CausalDAGResponse {
  nodes: string[];
  edges: Array<{ from: string; to: string; coefficient: number; description: string }>;
  total_nodes: number;
  total_edges: number;
  description: string;
}

// ── OCEMS Auto-Healer ──────────────────────────────────────
// Backend returns HealerDiagnosisResponse schema
export interface SensorDiagnosis {
  factory_id: string;
  parameter: string;
  diagnosis: string;
  confidence: number;
  indicators: Record<string, number>;
  severity: string;
  recommended_action: string;
  explanation: string;
}

export interface AutoHealerDiagnosis {
  factory_id: string;
  timestamp: string;
  diagnoses: SensorDiagnosis[];
  overall_health: number;
  dahs_uptime_pct: number;
}

export interface Factory {
  factory_id: string;
  factory_name: string;
  industry_type: string;
  industry_risk: string;
  state: string;
  district: string;
  ocems_installed: boolean;
}

// ── Gamification ───────────────────────────────────────────
export interface GamificationUser {
  user_id: string;
  username: string;
  city: string;
  eco_points: number;
  level: number;
  badges: string[];
  rank: number | null;
}

export interface LeaderboardEntry {
  rank: number;
  user_id: string;
  username: string;
  city: string;
  eco_points: number;
  level: number;
}

export type AQICategory = "Good" | "Satisfactory" | "Moderate" | "Poor" | "Very Poor" | "Severe";

export function getAQICategory(aqi: number): AQICategory {
  if (aqi <= 50) return "Good";
  if (aqi <= 100) return "Satisfactory";
  if (aqi <= 200) return "Moderate";
  if (aqi <= 300) return "Poor";
  if (aqi <= 400) return "Very Poor";
  return "Severe";
}

export function getAQIColor(aqi: number): string {
  if (aqi <= 50) return "#22c55e";   // green
  if (aqi <= 100) return "#84cc16";  // lime
  if (aqi <= 200) return "#eab308";  // yellow
  if (aqi <= 300) return "#f97316";  // orange
  if (aqi <= 400) return "#ef4444";  // red
  return "#991b1b";                   // dark red
}

export function getAQIBgClass(aqi: number): string {
  if (aqi <= 50) return "bg-green-500";
  if (aqi <= 100) return "bg-lime-500";
  if (aqi <= 200) return "bg-yellow-500";
  if (aqi <= 300) return "bg-orange-500";
  if (aqi <= 400) return "bg-red-500";
  return "bg-red-900";
}

export function getAQITextClass(aqi: number): string {
  if (aqi <= 50) return "text-green-600";
  if (aqi <= 100) return "text-lime-600";
  if (aqi <= 200) return "text-yellow-600";
  if (aqi <= 300) return "text-orange-600";
  if (aqi <= 400) return "text-red-600";
  return "text-red-900";
}
