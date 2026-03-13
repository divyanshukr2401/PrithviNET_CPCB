"use client";

import { useEffect, useState } from "react";
import { getFactories, diagnoseFactory } from "@/lib/api";
import type { AutoHealerDiagnosis, SensorDiagnosis, Factory } from "@/lib/types";
import {
  Shield,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  Factory as FactoryIcon,
  Wrench,
  Activity,
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

// ── Page Component ─────────────────────────────────────────
export default function CompliancePage() {
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

  // ── Load factories on mount ──────────────────────────────
  useEffect(() => {
    let cancelled = false;
    async function load() {
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
    load();
    return () => {
      cancelled = true;
    };
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
          OCEMS Auto-Healer
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Sensor fault detection vs real pollution analysis using 4-indicator weighted scoring.
          Diagnose factory OCEMS health and get actionable recommendations.
        </p>
      </div>

      {/* ═══════════════════════════════════════════════════════
          Factory Selector & Diagnose
          ═══════════════════════════════════════════════════════ */}
      <div className="bg-card rounded-lg border border-border p-5">
        <h2 className="text-sm font-medium text-muted-foreground mb-4">
          Select Factory
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
