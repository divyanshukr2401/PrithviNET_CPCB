"use client";

import { useEffect, useState } from "react";
import { getFactories, diagnoseFactory, getComplianceSummary, getExceedances } from "@/lib/api";
import type { AutoHealerDiagnosis, SensorDiagnosis, Factory } from "@/lib/types";
import {
  Shield,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  Factory as FactoryIcon,
  Wrench,
  Activity,
  TrendingUp,
  Gauge,
  TriangleAlert,
} from "lucide-react";

// ── Helpers ────────────────────────────────────────────────
function scoreColor(score: number): string {
  if (score > 80) return "text-green-400";
  if (score > 50) return "text-yellow-400";
  return "text-red-400";
}

function scoreRingColor(score: number): string {
  if (score > 80) return "#22c55e";
  if (score > 50) return "#eab308";
  return "#ef4444";
}

function scoreBgGlow(score: number): string {
  if (score > 80) return "shadow-green-500/20";
  if (score > 50) return "shadow-yellow-500/20";
  return "shadow-red-500/20";
}

function scoreLabel(score: number): string {
  if (score > 80) return "Healthy";
  if (score > 50) return "Degraded";
  return "Critical";
}

function severityColor(severity: string): string {
  switch (severity) {
    case "critical": return "text-red-400 bg-red-500/10 border-red-500/30";
    case "high": return "text-orange-400 bg-orange-500/10 border-orange-500/30";
    case "medium": return "text-yellow-400 bg-yellow-500/10 border-yellow-500/30";
    default: return "text-green-400 bg-green-500/10 border-green-500/30";
  }
}

function diagnosisColor(diagnosis: string): string {
  switch (diagnosis) {
    case "fault_detected": return "text-red-400";
    case "real_event": return "text-yellow-400";
    default: return "text-green-400";
  }
}

function formatIndicatorName(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function exceedanceColor(pct: number): string {
  if (pct > 200) return "text-red-400";
  if (pct > 100) return "text-orange-400";
  if (pct > 50) return "text-yellow-400";
  return "text-green-400";
}

// ── Exceedance type ───────────────────────────────────────
interface Exceedance {
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
}

// ── Compliance Summary type ───────────────────────────────
interface ComplianceSummaryData {
  total_factories: number;
  monitored_24h: number;
  compliant: number;
  non_compliant: number;
  critical: number;
  overall_compliance_pct: number;
  last_updated: string;
}

// ── Page Component ─────────────────────────────────────────
export default function CompliancePage() {
  // Compliance summary
  const [summary, setSummary] = useState<ComplianceSummaryData | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);

  // Exceedances
  const [exceedances, setExceedances] = useState<Exceedance[]>([]);
  const [excLoading, setExcLoading] = useState(true);

  // Factory list
  const [factories, setFactories] = useState<Factory[]>([]);
  const [factoriesLoading, setFactoriesLoading] = useState(true);
  const [factoriesError, setFactoriesError] = useState<string | null>(null);

  // Selected factory
  const [selectedFactoryId, setSelectedFactoryId] = useState<string>("");

  // Diagnosis
  const [diagnosis, setDiagnosis] = useState<AutoHealerDiagnosis | null>(null);
  const [diagLoading, setDiagLoading] = useState(false);
  const [diagError, setDiagError] = useState<string | null>(null);

  // ── Load summary + exceedances + factories on mount ─────
  useEffect(() => {
    let cancelled = false;

    async function loadSummary() {
      setSummaryLoading(true);
      try {
        const data = await getComplianceSummary();
        if (!cancelled) setSummary(data);
      } catch {
        // silently fail — summary is nice-to-have
      } finally {
        if (!cancelled) setSummaryLoading(false);
      }
    }

    async function loadExceedances() {
      setExcLoading(true);
      try {
        const data = await getExceedances({ hours: 72 });
        if (!cancelled) setExceedances(data.exceedances);
      } catch {
        // silently fail
      } finally {
        if (!cancelled) setExcLoading(false);
      }
    }

    async function loadFactories() {
      setFactoriesLoading(true);
      setFactoriesError(null);
      try {
        const data = await getFactories();
        if (!cancelled) {
          setFactories(data.factories);
          if (data.factories.length > 0) {
            setSelectedFactoryId(data.factories[0].factory_id);
          }
        }
      } catch (err) {
        if (!cancelled) {
          setFactoriesError(
            err instanceof Error ? err.message : "Failed to load factories"
          );
        }
      } finally {
        if (!cancelled) setFactoriesLoading(false);
      }
    }

    loadSummary();
    loadExceedances();
    loadFactories();
    return () => { cancelled = true; };
  }, []);

  // ── Diagnose handler ─────────────────────────────────────
  const handleDiagnose = async () => {
    if (!selectedFactoryId) return;
    setDiagLoading(true);
    setDiagError(null);
    setDiagnosis(null);
    try {
      const data = await diagnoseFactory(selectedFactoryId);
      setDiagnosis(data);
    } catch (err) {
      setDiagError(
        err instanceof Error ? err.message : "Diagnosis failed"
      );
    } finally {
      setDiagLoading(false);
    }
  };

  // ── Render ───────────────────────────────────────────────
  const selectedFactory = factories.find(
    (f) => f.factory_id === selectedFactoryId
  );

  // Derive summary from diagnoses
  const hasFault = diagnosis?.diagnoses.some((d) => d.diagnosis === "fault_detected") ?? false;
  const hasRealEvent = diagnosis?.diagnoses.some((d) => d.diagnosis === "real_event") ?? false;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Shield className="w-6 h-6 text-primary" />
          OCEMS Compliance & Auto-Healer
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Monitor factory compliance, view recent exceedances, and diagnose sensor health
          using 4-indicator weighted scoring.
        </p>
      </div>

      {/* ═══════════════════════════════════════════════════════
          Compliance Summary Dashboard
          ═══════════════════════════════════════════════════════ */}
      {summaryLoading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="bg-card rounded-lg border border-border p-4 animate-pulse">
              <div className="h-3 bg-muted/30 rounded w-20 mb-3" />
              <div className="h-8 bg-muted/20 rounded w-16" />
            </div>
          ))}
        </div>
      ) : summary && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="bg-card rounded-lg border border-border p-4">
            <div className="flex items-center gap-1.5 mb-2">
              <FactoryIcon className="w-3.5 h-3.5 text-muted-foreground" />
              <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">Total Factories</p>
            </div>
            <p className="text-2xl font-bold font-mono text-foreground">{summary.total_factories}</p>
          </div>
          <div className="bg-card rounded-lg border border-border p-4">
            <div className="flex items-center gap-1.5 mb-2">
              <Activity className="w-3.5 h-3.5 text-muted-foreground" />
              <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">Monitored 24h</p>
            </div>
            <p className="text-2xl font-bold font-mono text-foreground">{summary.monitored_24h}</p>
          </div>
          <div className="bg-card rounded-lg border border-border p-4">
            <div className="flex items-center gap-1.5 mb-2">
              <CheckCircle className="w-3.5 h-3.5 text-green-400" />
              <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">Compliant</p>
            </div>
            <p className="text-2xl font-bold font-mono text-green-400">{summary.compliant}</p>
          </div>
          <div className="bg-card rounded-lg border border-border p-4">
            <div className="flex items-center gap-1.5 mb-2">
              <AlertTriangle className="w-3.5 h-3.5 text-orange-400" />
              <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">Non-Compliant</p>
            </div>
            <p className="text-2xl font-bold font-mono text-orange-400">{summary.non_compliant}</p>
          </div>
          <div className="bg-card rounded-lg border border-border p-4">
            <div className="flex items-center gap-1.5 mb-2">
              <TriangleAlert className="w-3.5 h-3.5 text-red-400" />
              <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">Critical</p>
            </div>
            <p className="text-2xl font-bold font-mono text-red-400">{summary.critical}</p>
          </div>
          <div className="bg-card rounded-lg border border-border p-4">
            <div className="flex items-center gap-1.5 mb-2">
              <Gauge className="w-3.5 h-3.5 text-primary" />
              <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">Compliance</p>
            </div>
            <p className={`text-2xl font-bold font-mono ${summary.overall_compliance_pct >= 80 ? "text-green-400" : summary.overall_compliance_pct >= 50 ? "text-yellow-400" : "text-red-400"}`}>
              {summary.overall_compliance_pct.toFixed(0)}%
            </p>
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════
          Recent Exceedances (72h)
          ═══════════════════════════════════════════════════════ */}
      <div className="bg-card rounded-lg border border-border p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            Recent Exceedances (Last 72 Hours)
          </h2>
          {!excLoading && (
            <span className="text-xs text-muted-foreground">
              {exceedances.length} violation{exceedances.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>

        {excLoading ? (
          <div className="flex items-center gap-2 text-muted-foreground text-sm py-6 justify-center">
            <RefreshCw className="w-4 h-4 animate-spin" />
            Loading exceedances...
          </div>
        ) : exceedances.length === 0 ? (
          <div className="py-8 text-center">
            <CheckCircle className="w-8 h-8 text-green-400/40 mx-auto mb-2" />
            <p className="text-muted-foreground text-sm">No exceedances in the last 72 hours. All factories compliant.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-2.5 px-3 text-xs font-medium text-muted-foreground">Factory</th>
                  <th className="text-left py-2.5 px-3 text-xs font-medium text-muted-foreground">Parameter</th>
                  <th className="text-left py-2.5 px-3 text-xs font-medium text-muted-foreground">City</th>
                  <th className="text-right py-2.5 px-3 text-xs font-medium text-muted-foreground">Value</th>
                  <th className="text-right py-2.5 px-3 text-xs font-medium text-muted-foreground">Limit</th>
                  <th className="text-right py-2.5 px-3 text-xs font-medium text-muted-foreground">Exceedance</th>
                  <th className="text-left py-2.5 px-3 text-xs font-medium text-muted-foreground">Type</th>
                  <th className="text-left py-2.5 px-3 text-xs font-medium text-muted-foreground">Time</th>
                </tr>
              </thead>
              <tbody>
                {exceedances.slice(0, 20).map((exc, i) => (
                  <tr key={i} className="border-b border-border/50 hover:bg-muted/20 transition-colors">
                    <td className="py-2 px-3">
                      <span className="font-mono text-xs text-primary">{exc.factory_id}</span>
                    </td>
                    <td className="py-2 px-3 font-medium text-foreground">{exc.parameter}</td>
                    <td className="py-2 px-3 text-muted-foreground">{exc.city}</td>
                    <td className={`py-2 px-3 text-right font-mono font-medium ${exceedanceColor(exc.exceedance_pct)}`}>
                      {exc.value.toFixed(1)}
                    </td>
                    <td className="py-2 px-3 text-right font-mono text-muted-foreground">{exc.limit.toFixed(0)}</td>
                    <td className={`py-2 px-3 text-right font-mono font-bold ${exceedanceColor(exc.exceedance_pct)}`}>
                      +{exc.exceedance_pct.toFixed(0)}%
                    </td>
                    <td className="py-2 px-3">
                      <span className={`text-[10px] px-2 py-0.5 rounded-full border ${
                        exc.quality_flag === "suspect"
                          ? "text-yellow-400 bg-yellow-500/10 border-yellow-500/30"
                          : "text-red-400 bg-red-500/10 border-red-500/30"
                      }`}>
                        {exc.anomaly_type}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-xs text-muted-foreground whitespace-nowrap">
                      {new Date(exc.timestamp).toLocaleString("en-IN", {
                        day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", hour12: false,
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {exceedances.length > 20 && (
              <p className="text-xs text-muted-foreground text-center py-2 border-t border-border/50">
                Showing top 20 of {exceedances.length} exceedances (sorted by severity)
              </p>
            )}
          </div>
        )}
      </div>

      {/* ═══════════════════════════════════════════════════════
          Factory Selector & Diagnose
          ═══════════════════════════════════════════════════════ */}
      <div className="bg-card rounded-lg border border-border p-5">
        <h2 className="text-sm font-medium text-muted-foreground mb-4 flex items-center gap-2">
          <Wrench className="w-4 h-4" />
          OCEMS Auto-Healer — Select Factory to Diagnose
        </h2>

        {/* Factories loading */}
        {factoriesLoading && (
          <div className="flex items-center gap-2 text-muted-foreground text-sm py-4">
            <RefreshCw className="w-4 h-4 animate-spin" />
            Loading factories...
          </div>
        )}

        {/* Factories error */}
        {factoriesError && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-4 mb-4">
            <p className="text-red-400 font-medium text-sm">
              Failed to load factories
            </p>
            <p className="text-muted-foreground text-sm mt-1">
              {factoriesError}
            </p>
          </div>
        )}

        {/* Factories loaded but empty */}
        {!factoriesLoading && !factoriesError && factories.length === 0 && (
          <div className="py-6 text-center">
            <FactoryIcon className="w-8 h-8 text-muted-foreground/40 mx-auto mb-2" />
            <p className="text-muted-foreground text-sm">
              No factories found.
            </p>
          </div>
        )}

        {!factoriesLoading && factories.length > 0 && (
          <div className="flex flex-col sm:flex-row gap-4">
            {/* Dropdown */}
            <select
              value={selectedFactoryId}
              onChange={(e) => {
                setSelectedFactoryId(e.target.value);
                setDiagnosis(null);
                setDiagError(null);
              }}
              className="flex-1 rounded-lg border border-border bg-card text-foreground px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 appearance-none cursor-pointer"
            >
              {factories.map((f) => (
                <option key={f.factory_id} value={f.factory_id}>
                  {f.factory_id} - {f.factory_name} ({f.industry_type})
                </option>
              ))}
            </select>

            {/* Diagnose Button */}
            <button
              onClick={handleDiagnose}
              disabled={diagLoading || !selectedFactoryId}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
            >
              {diagLoading ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Wrench className="w-4 h-4" />
              )}
              {diagLoading ? "Diagnosing..." : "Diagnose"}
            </button>
          </div>
        )}

        {/* Selected factory info badge */}
        {selectedFactory && !factoriesLoading && (
          <div className="flex items-center gap-3 mt-4 pt-3 border-t border-border/50">
            <FactoryIcon className="w-4 h-4 text-muted-foreground" />
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="font-mono text-foreground font-medium">
                {selectedFactory.factory_id}
              </span>
              <span className="text-muted-foreground">|</span>
              <span className="text-muted-foreground">
                {selectedFactory.factory_name}
              </span>
              <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20">
                {selectedFactory.industry_type}
              </span>
              <span className={`px-2 py-0.5 rounded-full border text-[10px] ${severityColor(selectedFactory.industry_risk)}`}>
                {selectedFactory.industry_risk}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* ═══════════════════════════════════════════════════════
          Diagnosis Loading
          ═══════════════════════════════════════════════════════ */}
      {diagLoading && (
        <div className="bg-card rounded-lg border border-border p-12 text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-primary mx-auto mb-3" />
          <p className="text-muted-foreground text-sm">
            Running OCEMS diagnostics on {selectedFactoryId}...
          </p>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════
          Diagnosis Error
          ═══════════════════════════════════════════════════════ */}
      {diagError && (
        <div className="bg-card rounded-lg border border-red-500/30 p-5">
          <p className="text-red-400 font-medium text-sm">Diagnosis Error</p>
          <p className="text-muted-foreground text-sm mt-1">{diagError}</p>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════
          Diagnosis Empty State
          ═══════════════════════════════════════════════════════ */}
      {!diagLoading && !diagError && !diagnosis && (
        <div className="bg-card rounded-lg border border-border p-12 text-center">
          <Shield className="w-10 h-10 text-muted-foreground/40 mx-auto mb-3" />
          <p className="text-muted-foreground text-sm">
            Select a factory and click{" "}
            <span className="text-foreground font-medium">Diagnose</span> to
            run OCEMS sensor health analysis.
          </p>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════
          Diagnosis Results
          ═══════════════════════════════════════════════════════ */}
      {diagnosis && !diagLoading && (
        <div className="space-y-6">
          {/* Top row: Health gauge + Status badges */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Health Score Gauge */}
            <div
              className={`bg-card rounded-lg border border-border p-6 flex flex-col items-center justify-center shadow-lg ${scoreBgGlow(diagnosis.overall_health)}`}
            >
              <p className="text-xs font-medium text-muted-foreground mb-4">
                Overall Health Score
              </p>

              {/* Circular gauge */}
              <div className="relative w-40 h-40">
                <svg
                  className="w-full h-full -rotate-90"
                  viewBox="0 0 120 120"
                >
                  {/* Background ring */}
                  <circle
                    cx="60"
                    cy="60"
                    r="52"
                    fill="none"
                    stroke="#334155"
                    strokeWidth="10"
                  />
                  {/* Score ring */}
                  <circle
                    cx="60"
                    cy="60"
                    r="52"
                    fill="none"
                    stroke={scoreRingColor(diagnosis.overall_health)}
                    strokeWidth="10"
                    strokeLinecap="round"
                    strokeDasharray={`${((diagnosis.overall_health ?? 0) / 100) * 2 * Math.PI * 52} ${2 * Math.PI * 52}`}
                    className="transition-all duration-700 ease-out"
                  />
                </svg>
                {/* Center text */}
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span
                    className={`text-4xl font-bold font-mono ${scoreColor(diagnosis.overall_health)}`}
                  >
                    {Math.round(diagnosis.overall_health)}
                  </span>
                  <span className="text-xs text-muted-foreground mt-0.5">
                    / 100
                  </span>
                </div>
              </div>

              <p
                className={`text-sm font-medium mt-4 ${scoreColor(diagnosis.overall_health)}`}
              >
                {scoreLabel(diagnosis.overall_health)}
              </p>
            </div>

            {/* Status Badges & Summary */}
            <div className="lg:col-span-2 bg-card rounded-lg border border-border p-6 space-y-5">
              {/* Factory & Timestamp */}
              <div className="flex flex-wrap items-center gap-3 text-xs">
                <span className="font-mono text-foreground font-medium">
                  {diagnosis.factory_id}
                </span>
                <span className="text-muted-foreground">
                  {new Date(diagnosis.timestamp).toLocaleString()}
                </span>
                <span className="text-muted-foreground">|</span>
                <span className="text-muted-foreground">
                  DAHS Uptime: {(diagnosis.dahs_uptime_pct ?? 0).toFixed(1)}%
                </span>
              </div>

              {/* Fault & Pollution badges */}
              <div className="flex flex-wrap gap-3">
                <div
                  className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium ${
                    hasFault
                      ? "bg-red-500/10 text-red-400 border border-red-500/30"
                      : "bg-green-500/10 text-green-400 border border-green-500/30"
                  }`}
                >
                  {hasFault ? (
                    <AlertTriangle className="w-4 h-4" />
                  ) : (
                    <CheckCircle className="w-4 h-4" />
                  )}
                  {hasFault ? "Sensor Fault Detected" : "No Sensor Faults"}
                </div>

                <div
                  className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium ${
                    hasRealEvent
                      ? "bg-yellow-500/10 text-yellow-400 border border-yellow-500/30"
                      : "bg-green-500/10 text-green-400 border border-green-500/30"
                  }`}
                >
                  {hasRealEvent ? (
                    <AlertTriangle className="w-4 h-4" />
                  ) : (
                    <CheckCircle className="w-4 h-4" />
                  )}
                  {hasRealEvent ? "Real Pollution Detected" : "No Real Pollution"}
                </div>
              </div>

              {/* Summary stats */}
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-muted/20 rounded-lg p-3 text-center">
                  <p className="text-xs text-muted-foreground">Sensors</p>
                  <p className="text-lg font-bold font-mono text-foreground">{diagnosis.diagnoses.length}</p>
                </div>
                <div className="bg-muted/20 rounded-lg p-3 text-center">
                  <p className="text-xs text-muted-foreground">Faults</p>
                  <p className="text-lg font-bold font-mono text-red-400">
                    {diagnosis.diagnoses.filter((d) => d.diagnosis === "fault_detected").length}
                  </p>
                </div>
                <div className="bg-muted/20 rounded-lg p-3 text-center">
                  <p className="text-xs text-muted-foreground">Normal</p>
                  <p className="text-lg font-bold font-mono text-green-400">
                    {diagnosis.diagnoses.filter((d) => d.diagnosis === "normal").length}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* ═════════════════════════════════════════════════════
              Per-Sensor Diagnoses
              ═════════════════════════════════════════════════════ */}
          <div className="bg-card rounded-lg border border-border p-5">
            <h3 className="text-sm font-medium text-muted-foreground mb-4 flex items-center gap-2">
              <Activity className="w-4 h-4" />
              Per-Sensor Diagnosis
            </h3>

            <div className="space-y-3">
              {diagnosis.diagnoses.map((d: SensorDiagnosis, i: number) => (
                <div
                  key={`${d.parameter}-${i}`}
                  className="bg-muted/20 rounded-lg p-4"
                >
                  <div className="flex flex-wrap items-center gap-3 mb-2">
                    <span className="text-sm font-mono font-medium text-foreground">
                      {d.parameter}
                    </span>
                    <span className={`text-xs font-medium ${diagnosisColor(d.diagnosis)}`}>
                      {d.diagnosis.replace(/_/g, " ").toUpperCase()}
                    </span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full border ${severityColor(d.severity)}`}>
                      {d.severity}
                    </span>
                    <span className="text-xs text-muted-foreground ml-auto">
                      Confidence: {(d.confidence * 100).toFixed(0)}%
                    </span>
                  </div>

                  {/* Explanation */}
                  {d.explanation && (
                    <p className="text-xs text-muted-foreground mb-2">{d.explanation}</p>
                  )}

                  {/* Indicators */}
                  {Object.keys(d.indicators).length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-2">
                      {Object.entries(d.indicators).map(([key, value]) => (
                        <span
                          key={key}
                          className="text-[10px] font-mono px-2 py-0.5 rounded bg-card border border-border text-muted-foreground"
                        >
                          {formatIndicatorName(key)}: {typeof value === "number" ? value.toFixed(2) : String(value)}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Recommended action */}
                  {d.recommended_action && d.recommended_action !== "none" && (
                    <div className="flex items-center gap-2 text-xs mt-1">
                      <Wrench className="w-3 h-3 text-primary" />
                      <span className="text-primary">{d.recommended_action.replace(/_/g, " ")}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
