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

export interface OCEMSStandardsContext {
  standard_summary: string[];
  penalty_summary: string[];
  legal_summary: string[];
  authority: string;
}

export interface OCEMSNoticeDraft {
  to: string;
  cc: string[];
  subject: string;
  body: string;
  priority: string;
  status: string;
  disclaimer: string;
}

export interface OCEMSAlert {
  alert_id: string;
  factory_id: string;
  factory_name: string;
  industry_name: string;
  industry_type: string;
  cpcb_category: string | null;
  district: string | null;
  state: string | null;
  parameter: string;
  value: number;
  limit: number;
  exceedance_pct: number;
  severity: string;
  timestamp: string;
  anomaly_type: string;
  quality_flag: string;
  dahs_status: string;
  sensor_health: number;
  contact_email: string | null;
  contact_phone: string | null;
  website: string | null;
  ocems_type: string | null;
  air_pollutants: string | null;
  water_pollutants: string | null;
  solid_waste: string | null;
  raw_materials: string | null;
  diagnosis_summary: string;
  top_diagnosis: string | null;
  recommended_action: string | null;
  overall_health: number;
  dahs_uptime_pct: number;
  match_status: string;
  standards_context: OCEMSStandardsContext;
  notice_draft: OCEMSNoticeDraft;
}

export interface OCEMSAlertsSummary {
  total_units: number;
  active_alerts: number;
  critical_alerts: number;
  monitored_units: number;
  avg_compliance_signal: number;
  last_updated: string;
}

export interface OCEMSAlertsListResponse {
  alerts: OCEMSAlert[];
  total: number;
  filters: {
    district: string | null;
    cpcb_category: string | null;
    parameter: string | null;
    severity: string | null;
    hours: number;
  };
  filter_options: {
    districts: string[];
    cpcb_categories: string[];
    parameters: string[];
    severities: string[];
  };
}

export type UserRole =
  | "super_admin"
  | "regional_officer"
  | "monitoring_team"
  | "industry_user"
  | "citizen";

export interface AuthenticatedUser {
  user_id: string;
  username: string;
  full_name: string;
  role: UserRole;
  email?: string | null;
  phone?: string | null;
  city?: string | null;
  state?: string | null;
  is_active: boolean;
  auth_mode: string;
  assigned_region?: string | null;
  assigned_state?: string | null;
  assigned_district?: string | null;
  industry_scope?: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_at: string;
  user: AuthenticatedUser;
  role_home: string;
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
  district?: string;
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

// ── Groundwater Exploitation ─────────────────────────────────
export type ExploitationCategory =
  | "Safe"
  | "Semi-Critical"
  | "Critical"
  | "Over-Exploited";

export interface ExploitationStateData {
  state: string;
  rainfall_mm: number;
  extractable_ham: number;
  extraction_ham: number;
  exploitation_pct: number;
  category: ExploitationCategory;
}

export interface ExploitationDistrictData {
  state: string;
  district: string;
  rainfall_mm: number;
  recharge_ham: number;
  extractable_ham: number;
  extraction_ham: number;
  exploitation_pct: number;
  category: ExploitationCategory;
}

// ── Yearly AQI Forecast ─────────────────────────────────────
export interface DailyAQIPoint {
  date: string;        // "2025-04-01"
  avg_aqi: number;
  min_aqi: number;
  max_aqi: number;
}

export interface ForecastDailyPoint {
  date: string;        // "2026-04-01"
  predicted: number;
  lower: number;
  upper: number;
}

export interface MonthlySummary {
  month: string;       // "2025-04"
  avg_aqi: number;
  category: AQICategory;
  is_forecast: boolean;
}

export interface YearlyForecastResponse {
  station_id: string;
  station_name: string;
  city: string;
  historical: DailyAQIPoint[];
  forecast: ForecastDailyPoint[];
  monthly_summary: MonthlySummary[];
}

// ── Noise Monitoring ────────────────────────────────────────
export interface NoiseStation {
  station_id: string;
  station_name: string;
  city: string;
  latitude: number;
  longitude: number;
  zone: string;          // "industrial" | "commercial" | "residential" | "silence"
  leq: number;           // Current Leq dB(A)
  lmax: number;          // Current Lmax dB(A)
  lmin: number;          // Current Lmin dB(A)
  day_limit: number;
  night_limit: number;
  active_limit: number;  // Currently applicable limit
  is_exceedance: boolean;
  exceedance_db: number;
  period: string;        // "day" | "night"
  timestamp: string;
}

export interface NoiseLiveResponse {
  total_stations: number;
  period: string;
  exceedance_count: number;
  compliant_count: number;
  stations: NoiseStation[];
  last_updated: string;
}

export interface NoiseHistoricalPoint {
  hour: string;
  day_limit: number;
  night_limit: number;
  Leq_avg?: number;
  Leq_max?: number;
  Leq_min?: number;
  Lmax_avg?: number;
  Lmin_avg?: number;
  exceedances?: number;
}

export interface NoiseHistoricalResponse {
  station_id: string;
  hours: number;
  data: NoiseHistoricalPoint[];
  data_points: number;
}

// Noise compliance color scheme
export function getNoiseComplianceColor(leq: number, limit: number): string {
  const diff = leq - limit;
  if (diff > 0) return "#dc2626";      // Red — exceeding limit
  if (diff > -5) return "#eab308";     // Yellow — within 5 dB of limit
  return "#16a34a";                     // Green — well below limit
}

export function getNoiseComplianceLabel(leq: number, limit: number): string {
  const diff = leq - limit;
  if (diff > 0) return "Non-Compliant";
  if (diff > -5) return "Warning";
  return "Compliant";
}

export const ZONE_DISPLAY: Record<string, { label: string; color: string }> = {
  industrial:  { label: "Industrial",  color: "#f97316" },
  commercial:  { label: "Commercial",  color: "#3b82f6" },
  residential: { label: "Residential", color: "#22c55e" },
  silence:     { label: "Silence",     color: "#8b5cf6" },
};

// ── District-wise Noise Pollution Data ─────────────────────
export interface DistrictNoiseData {
  district_id: string;
  state: string;
  district: string;
  city_town: string;
  zone_type: string;           // "Industrial" | "Commercial" | "Residential" | "Silence"
  latitude: number;
  longitude: number;
  lday_dba: number;            // Day-time noise level dB(A)
  lnight_dba: number;          // Night-time noise level dB(A)
  leq_24hr_dba: number;        // 24-hour equivalent noise level dB(A)
  lden_dba: number;            // Day-evening-night weighted level dB(A)
  lmax_dba: number;            // Maximum noise level dB(A)
  std_day_db: number;          // CPCB standard day limit dB
  std_night_db: number;        // CPCB standard night limit dB
  exceed_day_db: number;       // Exceedance above day standard dB
  exceed_night_db: number;     // Exceedance above night standard dB
  compliance_day: string;      // "Compliant" | "Violation" | "Marginal"
  compliance_night: string;    // "Compliant" | "Violation" | "Marginal"
  risk_level: string;          // "Low" | "Moderate" | "High" | "Critical"
  primary_noise_source: string;
  data_source: string;
  year: number | null;
  notes: string | null;
}

export const RISK_LEVEL_COLORS: Record<string, string> = {
  Critical: "#7f1d1d",
  High:     "#dc2626",
  Moderate: "#eab308",
  Low:      "#16a34a",
};

export const COMPLIANCE_COLORS: Record<string, string> = {
  Violation: "#dc2626",
  Marginal:  "#eab308",
  Compliant: "#16a34a",
};

export function getDistrictNoiseMarkerColor(d: DistrictNoiseData): string {
  return RISK_LEVEL_COLORS[d.risk_level] || "#6b7280";
}
