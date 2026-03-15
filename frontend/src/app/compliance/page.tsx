"use client";

import { useEffect, useMemo, useState } from "react";
import {
  getOCEMSAlerts,
  getOCEMSAlertsSummary,
  getOCEMSNoticeDraft,
  diagnoseFactory,
} from "@/lib/api";
import type {
  AutoHealerDiagnosis,
  OCEMSAlert,
  OCEMSAlertsSummary,
  OCEMSNoticeDraft,
} from "@/lib/types";
import {
  AlertTriangle,
  BellRing,
  CheckCircle2,
  Factory,
  FileText,
  Gauge,
  Loader2,
  Mail,
  Phone,
  RefreshCw,
  ShieldAlert,
  Siren,
  Sparkles,
  TriangleAlert,
  Wand2,
  X,
} from "lucide-react";

type AlertFilters = {
  district: string;
  cpcbCategory: string;
  parameter: string;
  severity: string;
};

function severityBadge(severity: string): string {
  switch (severity) {
    case "critical":
      return "border-red-500/30 bg-red-500/10 text-red-700";
    case "high":
      return "border-orange-500/30 bg-orange-500/10 text-orange-700";
    case "medium":
      return "border-amber-500/30 bg-amber-500/10 text-amber-700";
    default:
      return "border-emerald-500/30 bg-emerald-500/10 text-emerald-700";
  }
}

function severityText(exceedancePct: number): string {
  if (exceedancePct >= 200) return "Immediate board review";
  if (exceedancePct >= 100) return "Urgent mitigation required";
  if (exceedancePct >= 50) return "Corrective action required";
  return "Monitor closely";
}

function diagnosisTone(diagnosis: string | null): string {
  switch (diagnosis) {
    case "fault_detected":
      return "text-red-700";
    case "real_event":
      return "text-orange-700";
    case "suspect":
      return "text-amber-700";
    default:
      return "text-emerald-700";
  }
}

function complianceTone(value: number): string {
  if (value >= 90) return "text-emerald-700";
  if (value >= 75) return "text-amber-700";
  return "text-red-700";
}

function formatDateTime(value: string): string {
  if (!value) return "-";
  return new Date(value).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function InfoRow({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="flex items-start justify-between gap-4 py-2 border-b border-border/50 last:border-b-0">
      <span className="text-xs uppercase tracking-wide text-muted-foreground">{label}</span>
      <span className="text-sm text-right text-foreground max-w-[70%] break-words">{value || "Not available"}</span>
    </div>
  );
}

function NoticeModal({
  open,
  draft,
  loading,
  onClose,
}: {
  open: boolean;
  draft: OCEMSNoticeDraft | null;
  loading: boolean;
  onClose: () => void;
}) {
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");

  useEffect(() => {
    setSubject(draft?.subject || "");
    setBody(draft?.body || "");
  }, [draft]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 px-4">
      <div className="w-full max-w-3xl rounded-2xl border border-border bg-card shadow-2xl">
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <div>
            <h3 className="text-lg font-semibold text-foreground">Draft Non-Compliance Notice</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-border p-2 text-muted-foreground hover:bg-muted/40"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-4 px-6 py-5">
          {loading ? (
            <div className="flex items-center justify-center gap-2 py-12 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Preparing draft notice...
            </div>
          ) : (
            <>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-muted-foreground">To</label>
                  <input
                    value={draft?.to || ""}
                    readOnly
                    className="w-full rounded-lg border border-border bg-muted/20 px-3 py-2 text-sm text-foreground"
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-muted-foreground">CC</label>
                  <input
                    value={draft?.cc?.join(", ") || ""}
                    readOnly
                    className="w-full rounded-lg border border-border bg-muted/20 px-3 py-2 text-sm text-foreground"
                  />
                </div>
              </div>

              <div>
                <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Subject</label>
                <input
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                />
              </div>

              <div>
                <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Body</label>
                <textarea
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  rows={14}
                  className="w-full rounded-lg border border-border bg-card px-3 py-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 resize-none"
                />
              </div>

            </>
          )}
        </div>

        <div className="flex items-center justify-between border-t border-border px-6 py-4">
          <div className="text-xs text-muted-foreground">
            Status: <span className="font-medium text-foreground">{draft?.status || "draft_ready"}</span>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-border px-4 py-2 text-sm text-foreground hover:bg-muted/40"
            >
              Close
            </button>
            <button
              type="button"
              className="rounded-lg border border-sky-500/30 bg-sky-500/10 px-4 py-2 text-sm font-medium text-sky-700"
            >
              Save Draft
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function CompliancePage() {
  const [summary, setSummary] = useState<OCEMSAlertsSummary | null>(null);
  const [alerts, setAlerts] = useState<OCEMSAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<AlertFilters>({
    district: "",
    cpcbCategory: "",
    parameter: "",
    severity: "",
  });
  const [filterOptions, setFilterOptions] = useState<{
    districts: string[];
    cpcb_categories: string[];
    parameters: string[];
    severities: string[];
  }>({
    districts: [],
    cpcb_categories: [],
    parameters: [],
    severities: ["critical", "high", "medium", "low"],
  });
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);
  const [noticeOpen, setNoticeOpen] = useState(false);
  const [noticeDraft, setNoticeDraft] = useState<OCEMSNoticeDraft | null>(null);
  const [noticeLoading, setNoticeLoading] = useState(false);
  const [diagnosisLoading, setDiagnosisLoading] = useState(false);
  const [diagnosis, setDiagnosis] = useState<AutoHealerDiagnosis | null>(null);

  const selectedAlert = useMemo(
    () => alerts.find((alert) => alert.alert_id === selectedAlertId) || alerts[0] || null,
    [alerts, selectedAlertId]
  );

  async function loadAlerts() {
    setLoading(true);
    setError(null);
    try {
      const [summaryData, alertsData] = await Promise.all([
        getOCEMSAlertsSummary({ hours: 72 }),
        getOCEMSAlerts({
          district: filters.district || undefined,
          cpcb_category: filters.cpcbCategory || undefined,
          parameter: filters.parameter || undefined,
          severity: filters.severity || undefined,
          hours: 72,
        }),
      ]);
      setSummary(summaryData);
      setAlerts(alertsData.alerts);
      setFilterOptions(alertsData.filter_options);
      setSelectedAlertId((prev) => {
        if (prev && alertsData.alerts.some((alert) => alert.alert_id === prev)) {
          return prev;
        }
        return alertsData.alerts[0]?.alert_id || null;
      });
      setDiagnosis(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load alerts");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadAlerts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.district, filters.cpcbCategory, filters.parameter, filters.severity]);

  async function handleDiagnose(alert: OCEMSAlert) {
    setDiagnosisLoading(true);
    try {
      const result = await diagnoseFactory(alert.factory_id, {
        parameter: alert.parameter,
        hours: 6,
      });
      setDiagnosis(result);
    } catch {
      setDiagnosis(null);
    } finally {
      setDiagnosisLoading(false);
    }
  }

  async function handleOpenNotice(alert: OCEMSAlert) {
    setNoticeOpen(true);
    setNoticeLoading(true);
    setNoticeDraft(null);
    try {
      const draft = await getOCEMSNoticeDraft(alert.alert_id);
      setNoticeDraft(draft);
    } catch {
      setNoticeDraft(alert.notice_draft);
    } finally {
      setNoticeLoading(false);
    }
  }

  return (
    <>
      <div className="space-y-6">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="flex items-center gap-2 text-2xl font-bold text-foreground">
              <ShieldAlert className="h-6 w-6 text-red-700" />
              OCEMS Alerts
            </h1>
            <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
              Alert-first regulator workspace for industrial exceedances, contact enrichment,
              legal context, OCEMS diagnostics, and believable notice drafting.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void loadAlerts()}
            className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm text-foreground hover:bg-muted/40"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh Alerts
          </button>
        </div>

        <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
          <div className="rounded-2xl border border-border bg-card p-4">
            <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground">
              <Factory className="h-3.5 w-3.5" /> Total Units
            </div>
            <div className="text-2xl font-bold text-foreground">{summary?.total_units ?? 0}</div>
          </div>
          <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-4">
            <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-wide text-red-700">
              <BellRing className="h-3.5 w-3.5" /> Active Alerts
            </div>
            <div className="text-2xl font-bold text-red-700">{summary?.active_alerts ?? 0}</div>
          </div>
          <div className="rounded-2xl border border-orange-500/20 bg-orange-500/5 p-4">
            <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-wide text-orange-700">
              <Siren className="h-3.5 w-3.5" /> Critical Alerts
            </div>
            <div className="text-2xl font-bold text-orange-700">{summary?.critical_alerts ?? 0}</div>
          </div>
          <div className="rounded-2xl border border-border bg-card p-4">
            <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground">
              <CheckCircle2 className="h-3.5 w-3.5" /> Monitored
            </div>
            <div className="text-2xl font-bold text-foreground">{summary?.monitored_units ?? 0}</div>
          </div>
          <div className="rounded-2xl border border-border bg-card p-4">
            <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground">
              <Gauge className="h-3.5 w-3.5" /> Compliance Signal
            </div>
            <div className={`text-2xl font-bold ${complianceTone(summary?.avg_compliance_signal ?? 0)}`}>
              {(summary?.avg_compliance_signal ?? 0).toFixed(0)}%
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-card p-5">
          <div className="mb-4 flex items-center gap-2 text-sm font-medium text-foreground">
            <Sparkles className="h-4 w-4 text-primary" /> Alert Filters
          </div>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <select
              value={filters.district}
              onChange={(e) => setFilters((prev) => ({ ...prev, district: e.target.value }))}
              className="rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
            >
              <option value="">All districts</option>
              {filterOptions.districts.map((district) => (
                <option key={district} value={district}>{district}</option>
              ))}
            </select>
            <select
              value={filters.cpcbCategory}
              onChange={(e) => setFilters((prev) => ({ ...prev, cpcbCategory: e.target.value }))}
              className="rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
            >
              <option value="">All CPCB categories</option>
              {filterOptions.cpcb_categories.map((category) => (
                <option key={category} value={category}>{category}</option>
              ))}
            </select>
            <select
              value={filters.parameter}
              onChange={(e) => setFilters((prev) => ({ ...prev, parameter: e.target.value }))}
              className="rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
            >
              <option value="">All parameters</option>
              {filterOptions.parameters.map((param) => (
                <option key={param} value={param}>{param}</option>
              ))}
            </select>
            <select
              value={filters.severity}
              onChange={(e) => setFilters((prev) => ({ ...prev, severity: e.target.value }))}
              className="rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
            >
              <option value="">All severities</option>
              {filterOptions.severities.map((level) => (
                <option key={level} value={level}>{level}</option>
              ))}
            </select>
          </div>
        </div>

        {error && (
          <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="grid gap-5 xl:grid-cols-12">
          <div className="xl:col-span-7 rounded-2xl border border-border bg-card overflow-hidden">
            <div className="flex items-center justify-between border-b border-border px-5 py-4">
              <div>
                <h2 className="text-sm font-semibold text-foreground">Active OCEMS Alerts</h2>
                <p className="text-xs text-muted-foreground">
                  {loading ? "Loading latest alert stream..." : `${alerts.length} enriched alert${alerts.length === 1 ? "" : "s"}`}
                </p>
              </div>
            </div>

            {loading ? (
              <div className="flex items-center justify-center gap-2 py-14 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading OCEMS Alerts...
              </div>
            ) : alerts.length === 0 ? (
              <div className="space-y-3 px-6 py-14 text-center">
                <CheckCircle2 className="mx-auto h-10 w-10 text-emerald-600/40" />
                <div className="text-lg font-semibold text-foreground">No active alerts in the selected window</div>
                <p className="mx-auto max-w-xl text-sm text-muted-foreground">
                  Telemetry is currently within configured OCEMS limits. The alert workspace is ready and will populate automatically when a live exceedance is detected.
                </p>
              </div>
            ) : (
              <div className="max-h-[860px] overflow-y-auto">
                {alerts.map((alert) => {
                  const active = alert.alert_id === selectedAlert?.alert_id;
                  return (
                    <button
                      key={alert.alert_id}
                      type="button"
                      onClick={() => {
                        setSelectedAlertId(alert.alert_id);
                        setDiagnosis(null);
                      }}
                      className={`w-full border-b border-border/60 px-5 py-4 text-left transition-colors hover:bg-muted/30 ${
                        active ? "bg-muted/30" : "bg-card"
                      }`}
                    >
                      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                        <div className="space-y-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className={`rounded-full border px-2.5 py-1 text-[11px] font-medium uppercase tracking-wide ${severityBadge(alert.severity)}`}>
                              {alert.severity}
                            </span>
                            <span className="rounded-full border border-border px-2.5 py-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                              {alert.parameter}
                            </span>
                            {alert.cpcb_category && (
                              <span className="rounded-full border border-border px-2.5 py-1 text-[11px] font-medium uppercase tracking-wide text-foreground">
                                {alert.cpcb_category}
                              </span>
                            )}
                          </div>
                          <div>
                            <div className="text-base font-semibold text-foreground">{alert.industry_name}</div>
                            <div className="text-sm text-muted-foreground">
                              {alert.district || alert.factory_name} {alert.state ? `, ${alert.state}` : ""}
                            </div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-xl font-bold text-foreground">
                            {alert.value.toFixed(1)}
                          </div>
                          <div className="text-xs text-muted-foreground">Limit {alert.limit.toFixed(0)}</div>
                          <div className={`mt-1 text-sm font-semibold ${severityBadge(alert.severity).split(" ").find((c) => c.startsWith("text-")) || "text-red-700"}`}>
                            +{alert.exceedance_pct.toFixed(0)}%
                          </div>
                        </div>
                      </div>

                      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs">
                        <div className="text-muted-foreground">
                          {severityText(alert.exceedance_pct)} · {formatDateTime(alert.timestamp)}
                        </div>
                        <div className={`font-medium ${diagnosisTone(alert.top_diagnosis)}`}>
                          {alert.top_diagnosis ? alert.top_diagnosis.replace(/_/g, " ") : "diagnosis pending"}
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <div className="xl:col-span-5 rounded-2xl border border-border bg-card overflow-hidden">
            <div className="border-b border-border px-5 py-4">
              <h2 className="text-sm font-semibold text-foreground">Alert Detail</h2>
              <p className="text-xs text-muted-foreground">
                Contact enrichment, legal context, diagnostic summary, and notice drafting
              </p>
            </div>

            {!selectedAlert ? (
              <div className="px-6 py-14 text-center text-sm text-muted-foreground">
                Select an alert to review details.
              </div>
            ) : (
              <div className="max-h-[860px] overflow-y-auto px-5 py-5">
                <div className="space-y-4">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`rounded-full border px-2.5 py-1 text-[11px] font-medium uppercase tracking-wide ${severityBadge(selectedAlert.severity)}`}>
                        {selectedAlert.severity}
                      </span>
                      <span className="rounded-full border border-border px-2.5 py-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                        {selectedAlert.match_status}
                      </span>
                    </div>
                    <h3 className="mt-3 text-xl font-semibold text-foreground">{selectedAlert.industry_name}</h3>
                    <p className="text-sm text-muted-foreground">
                      {selectedAlert.industry_type} · {selectedAlert.factory_id}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-xl border border-border bg-muted/20 p-3">
                      <div className="text-xs uppercase tracking-wide text-muted-foreground">Current Value</div>
                      <div className="mt-1 text-xl font-bold text-foreground">{selectedAlert.value.toFixed(1)}</div>
                    </div>
                    <div className="rounded-xl border border-border bg-muted/20 p-3">
                      <div className="text-xs uppercase tracking-wide text-muted-foreground">Applicable Limit</div>
                      <div className="mt-1 text-xl font-bold text-foreground">{selectedAlert.limit.toFixed(1)}</div>
                    </div>
                    <div className="rounded-xl border border-border bg-muted/20 p-3">
                      <div className="text-xs uppercase tracking-wide text-muted-foreground">Sensor Health</div>
                      <div className="mt-1 text-xl font-bold text-foreground">{selectedAlert.sensor_health.toFixed(0)}%</div>
                    </div>
                    <div className="rounded-xl border border-border bg-muted/20 p-3">
                      <div className="text-xs uppercase tracking-wide text-muted-foreground">DAHS Uptime</div>
                      <div className="mt-1 text-xl font-bold text-foreground">{selectedAlert.dahs_uptime_pct.toFixed(0)}%</div>
                    </div>
                  </div>

                  <div className="rounded-xl border border-border p-4">
                    <div className="mb-3 flex items-center gap-2 text-sm font-medium text-foreground">
                      <Factory className="h-4 w-4 text-primary" /> Unit & Contact Profile
                    </div>
                    <InfoRow label="District" value={selectedAlert.district} />
                    <InfoRow label="State" value={selectedAlert.state} />
                    <InfoRow label="Email" value={selectedAlert.contact_email} />
                    <InfoRow label="Phone" value={selectedAlert.contact_phone} />
                    <InfoRow label="Website" value={selectedAlert.website} />
                    <InfoRow label="OCEMS Type" value={selectedAlert.ocems_type} />
                    <InfoRow label="Air Pollutants" value={selectedAlert.air_pollutants} />
                    <InfoRow label="Water Pollutants" value={selectedAlert.water_pollutants} />
                    <InfoRow label="Hazardous Waste" value={selectedAlert.solid_waste} />
                  </div>

                  <div className="rounded-xl border border-border p-4">
                    <div className="mb-3 flex items-center gap-2 text-sm font-medium text-foreground">
                      <TriangleAlert className="h-4 w-4 text-orange-700" /> Alert Interpretation
                    </div>
                    <p className="text-sm text-foreground">{selectedAlert.diagnosis_summary}</p>
                    <div className={`mt-3 text-sm font-medium ${diagnosisTone(selectedAlert.top_diagnosis)}`}>
                      Diagnostic classification: {(selectedAlert.top_diagnosis || "pending").replace(/_/g, " ")}
                    </div>
                    {selectedAlert.recommended_action && (
                      <div className="mt-2 text-sm text-muted-foreground">
                        Recommended action: {selectedAlert.recommended_action.replace(/_/g, " ")}
                      </div>
                    )}
                  </div>

                  <div className="rounded-xl border border-border p-4">
                    <div className="mb-3 flex items-center gap-2 text-sm font-medium text-foreground">
                      <FileText className="h-4 w-4 text-sky-700" /> Standards & Legal Context
                    </div>
                    <div className="space-y-3 text-sm text-foreground">
                      <div>
                        <div className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">Standards Snapshot</div>
                        <ul className="space-y-1 text-sm text-foreground">
                          {selectedAlert.standards_context.standard_summary.map((line, index) => (
                            <li key={index}>- {line}</li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <div className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">Penalty / Enforcement Notes</div>
                        <ul className="space-y-1 text-sm text-foreground">
                          {selectedAlert.standards_context.penalty_summary.map((line, index) => (
                            <li key={index}>- {line}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2">
                    <button
                      type="button"
                      onClick={() => void handleDiagnose(selectedAlert)}
                      className="inline-flex items-center justify-center gap-2 rounded-xl border border-primary/30 bg-primary/10 px-4 py-3 text-sm font-medium text-primary hover:bg-primary/15"
                    >
                      {diagnosisLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />}
                      Run Diagnostic
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleOpenNotice(selectedAlert)}
                      className="inline-flex items-center justify-center gap-2 rounded-xl border border-sky-500/30 bg-sky-500/10 px-4 py-3 text-sm font-medium text-sky-700 hover:bg-sky-500/15"
                    >
                      <Mail className="h-4 w-4" /> Draft Notice
                    </button>
                  </div>

                  {diagnosis && diagnosis.factory_id === selectedAlert.factory_id && (
                    <div className="rounded-xl border border-border p-4">
                      <div className="mb-2 flex items-center gap-2 text-sm font-medium text-foreground">
                        <Sparkles className="h-4 w-4 text-primary" /> Auto-Healer Result
                      </div>
                      <div className="mb-3 text-sm text-muted-foreground">
                        Overall health {diagnosis.overall_health.toFixed(0)}% · DAHS uptime {diagnosis.dahs_uptime_pct.toFixed(0)}%
                      </div>
                      <div className="space-y-3">
                        {diagnosis.diagnoses.map((item) => (
                          <div key={`${item.factory_id}-${item.parameter}`} className="rounded-xl border border-border bg-muted/20 p-3">
                            <div className="flex items-center justify-between gap-3">
                              <div className="text-sm font-semibold text-foreground">{item.parameter}</div>
                              <div className={`text-xs font-medium uppercase tracking-wide ${diagnosisTone(item.diagnosis)}`}>
                                {item.diagnosis.replace(/_/g, " ")}
                              </div>
                            </div>
                            <p className="mt-2 text-sm text-muted-foreground">{item.explanation}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <NoticeModal
        open={noticeOpen}
        draft={noticeDraft}
        loading={noticeLoading}
        onClose={() => setNoticeOpen(false)}
      />
    </>
  );
}
