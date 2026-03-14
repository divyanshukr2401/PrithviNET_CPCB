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

// Official CPCB AQI color hex values
export const CPCB_AQI_COLORS: Record<AQICategory, string> = {
  Good: "#009966",
  Satisfactory: "#58FF09",
  Moderate: "#FFDE33",
  Poor: "#FF9933",
  "Very Poor": "#FF0000",
  Severe: "#800000",
};

// Text color for readability on each CPCB background
export const CPCB_AQI_TEXT_COLORS: Record<AQICategory, string> = {
  Good: "#ffffff",
  Satisfactory: "#1a1a1a",
  Moderate: "#1a1a1a",
  Poor: "#ffffff",
  "Very Poor": "#ffffff",
  Severe: "#ffffff",
};

// CPCB health impact descriptions
export const CPCB_AQI_HEALTH_IMPACTS: Record<AQICategory, string> = {
  Good: "Minimal impact",
  Satisfactory: "May cause minor breathing discomfort to sensitive people",
  Moderate: "May cause breathing discomfort to people with lung disease such as asthma, and discomfort to people with heart disease, children and older adults",
  Poor: "May cause breathing discomfort to people on prolonged exposure, and discomfort to people with heart disease",
  "Very Poor": "May cause respiratory illness to the people on prolonged exposure. Effect may be more pronounced in people with lung and heart diseases",
  Severe: "May cause respiratory impact even on healthy people, and serious health impacts on people with lung/heart disease. The health impacts may be experienced even during light physical activity",
};

// AQI range strings for display
export const CPCB_AQI_RANGES: Record<AQICategory, string> = {
  Good: "0-50",
  Satisfactory: "51-100",
  Moderate: "101-200",
  Poor: "201-300",
  "Very Poor": "301-400",
  Severe: "401-500",
};

export const AQI_CATEGORIES_ORDERED: AQICategory[] = [
  "Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe",
];

export function getAQIColor(aqi: number): string {
  return CPCB_AQI_COLORS[getAQICategory(aqi)];
}

export function getAQITextOnColor(aqi: number): string {
  return CPCB_AQI_TEXT_COLORS[getAQICategory(aqi)];
}

// ── Water Quality Heatmap ──────────────────────────────────
export interface WaterQualityHeatmapPoint {
  lat: number;
  lng: number;
  intensity: number;
  station_name: string;
  state: string;
  station_code: string;
  wqi: number;
  parameters: Record<string, number>;
}

export interface WaterQualityHeatmapResponse {
  source: string;
  total_points: number;
  filter: { state: string | null; limit: number };
  points: WaterQualityHeatmapPoint[];
}

// ── Groundwater Level ──────────────────────────────────────
export interface GroundwaterBand {
  range: string;
  count: number;
  percentage: number;
}

export interface GroundwaterClassification {
  level: string;
  color: string;
  description: string;
}

export interface GroundwaterCity {
  city: string;
  wells_analysed: number;
  depth_min_mbgl: number | null;
  depth_max_mbgl: number | null;
  avg_depth_mbgl: number;
  bands: GroundwaterBand[];
  classification: GroundwaterClassification;
}

export interface GroundwaterResponse {
  source: string;
  total_cities: number;
  filter: { city: string | null };
  cities: GroundwaterCity[];
}
