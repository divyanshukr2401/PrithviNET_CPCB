"use client";

import { useEffect, useState } from "react";
import { getLeaderboard, submitReport } from "@/lib/api";
import type { LeaderboardEntry } from "@/lib/types";
import { Trophy, Medal, Star, Send, Users, RefreshCw, MapPin } from "lucide-react";

// ── Categories — map to backend CitizenReport.report_type ──
const REPORT_CATEGORIES = [
  { value: "air_pollution", label: "Air Pollution" },
  { value: "water_pollution", label: "Water Pollution" },
  { value: "noise_violation", label: "Noise Violation" },
  { value: "illegal_dumping", label: "Illegal Dumping" },
] as const;

const SEVERITY_OPTIONS = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "critical", label: "Critical" },
] as const;

// ── Level names (same as backend LEVELS) ──────────────────
const LEVEL_NAMES = [
  "Seedling",
  "Sprout",
  "Sapling",
  "Tree",
  "Forest",
  "Ecosystem",
  "Climate Champion",
  "Biosphere Guardian",
];

function getLevelName(level: number): string {
  return LEVEL_NAMES[Math.min(level - 1, LEVEL_NAMES.length - 1)] ?? "Seedling";
}

// ── Helpers ───────────────────────────────────────────────
function rankIcon(rank: number) {
  if (rank === 1) return <Trophy className="w-4 h-4 text-yellow-600" />;
  if (rank === 2) return <Medal className="w-4 h-4 text-gray-500" />;
  if (rank === 3) return <Medal className="w-4 h-4 text-amber-700" />;
  return <span className="w-4 text-center text-xs text-muted-foreground font-mono">{rank}</span>;
}

// ── Page Component ────────────────────────────────────────
export default function GamificationPage() {
  // Leaderboard state
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [lbLoading, setLbLoading] = useState(true);
  const [lbError, setLbError] = useState<string | null>(null);

  // Report form state
  const [userId, setUserId] = useState("");
  const [reportType, setReportType] = useState<string>(REPORT_CATEGORIES[0].value);
  const [description, setDescription] = useState("");
  const [severity, setSeverity] = useState("medium");
  const [latitude, setLatitude] = useState(21.25);
  const [longitude, setLongitude] = useState(81.63);
  const [geoLoading, setGeoLoading] = useState(false);

  // Submission state
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitResult, setSubmitResult] = useState<{
    status: string;
    report_id: string;
    points_awarded: number;
  } | null>(null);

  // ── Load leaderboard on mount ───────────────────────────
  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLbLoading(true);
      setLbError(null);
      try {
        // Backend returns array directly
        const data = await getLeaderboard();
        if (!cancelled) {
          setLeaderboard(data);
        }
      } catch (err) {
        if (!cancelled) {
          setLbError(
            err instanceof Error ? err.message : "Failed to load leaderboard"
          );
        }
      } finally {
        if (!cancelled) setLbLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  // ── Submit report handler ───────────────────────────────
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userId.trim() || !description.trim()) return;

    setSubmitting(true);
    setSubmitError(null);
    setSubmitResult(null);
    try {
      const result = await submitReport({
        user_id: userId.trim(),
        report_type: reportType,
        description: description.trim(),
        latitude,
        longitude,
        severity,
      });
      setSubmitResult(result);
      // Clear form after successful submission
      setDescription("");
      setSeverity("medium");
      // Refresh leaderboard after successful submission
      try {
        const lbData = await getLeaderboard();
        setLeaderboard(lbData);
      } catch {
        // silently ignore leaderboard refresh failure
      }
    } catch (err) {
      setSubmitError(
        err instanceof Error ? err.message : "Failed to submit report"
      );
    } finally {
      setSubmitting(false);
    }
  };

  // ── Render ──────────────────────────────────────────────
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Trophy className="w-6 h-6 text-primary" />
          Eco Points Portal
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Submit environmental reports and earn eco points. Climb the
          leaderboard by contributing to environmental monitoring.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ═══════════════════════════════════════════════════
            Submit Report Form
            ═══════════════════════════════════════════════════ */}
        <div className="bg-card rounded-lg border border-border p-5">
          <h2 className="text-sm font-medium text-muted-foreground mb-4 flex items-center gap-2">
            <Send className="w-4 h-4" />
            Submit Report
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* User ID */}
            <div>
              <label
                htmlFor="user-id"
                className="block text-xs font-medium text-muted-foreground mb-1.5"
              >
                User ID
              </label>
              <input
                id="user-id"
                type="text"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                placeholder="e.g. citizen_raipur_01"
                required
                className="w-full rounded-lg border border-border bg-card text-foreground px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 placeholder:text-muted-foreground/50"
              />
            </div>

            {/* Category / Report Type */}
            <div>
              <label
                htmlFor="report-type"
                className="block text-xs font-medium text-muted-foreground mb-1.5"
              >
                Report Type
              </label>
              <select
                id="report-type"
                value={reportType}
                onChange={(e) => setReportType(e.target.value)}
                className="w-full rounded-lg border border-border bg-card text-foreground px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              >
                {REPORT_CATEGORIES.map((cat) => (
                  <option key={cat.value} value={cat.value}>
                    {cat.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Description */}
            <div>
              <label
                htmlFor="description"
                className="block text-xs font-medium text-muted-foreground mb-1.5"
              >
                Description
              </label>
              <textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe the environmental issue you observed..."
                required
                rows={4}
                className="w-full rounded-lg border border-border bg-card text-foreground px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 placeholder:text-muted-foreground/50 resize-none"
              />
            </div>

            {/* Severity */}
            <div>
              <label
                htmlFor="severity"
                className="block text-xs font-medium text-muted-foreground mb-1.5"
              >
                Severity
              </label>
              <select
                id="severity"
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
                className="w-full rounded-lg border border-border bg-card text-foreground px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              >
                {SEVERITY_OPTIONS.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
              <p className="text-[10px] text-muted-foreground mt-1">
                Higher severity = more eco-points awarded
              </p>
            </div>

            {/* Lat / Lng with Geolocation */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-medium text-muted-foreground">
                  Location
                </label>
                <button
                  type="button"
                  onClick={() => {
                    if (!navigator.geolocation) return;
                    setGeoLoading(true);
                    navigator.geolocation.getCurrentPosition(
                      (pos) => {
                        setLatitude(parseFloat(pos.coords.latitude.toFixed(6)));
                        setLongitude(parseFloat(pos.coords.longitude.toFixed(6)));
                        setGeoLoading(false);
                      },
                      () => setGeoLoading(false),
                      { enableHighAccuracy: true, timeout: 10000 }
                    );
                  }}
                  disabled={geoLoading}
                  className="inline-flex items-center gap-1 text-[10px] text-primary hover:text-primary/80 transition-colors font-medium"
                >
                  {geoLoading ? (
                    <RefreshCw className="w-3 h-3 animate-spin" />
                  ) : (
                    <MapPin className="w-3 h-3" />
                  )}
                  {geoLoading ? "Detecting..." : "Use my location"}
                </button>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label
                    htmlFor="latitude"
                    className="block text-[10px] text-muted-foreground mb-1"
                  >
                    Latitude
                  </label>
                  <input
                    id="latitude"
                    type="number"
                    step="any"
                    value={latitude}
                    onChange={(e) => setLatitude(parseFloat(e.target.value) || 0)}
                    className="w-full rounded-lg border border-border bg-card text-foreground px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 font-mono"
                  />
                </div>
                <div>
                  <label
                    htmlFor="longitude"
                    className="block text-[10px] text-muted-foreground mb-1"
                  >
                    Longitude
                  </label>
                  <input
                    id="longitude"
                    type="number"
                    step="any"
                    value={longitude}
                    onChange={(e) => setLongitude(parseFloat(e.target.value) || 0)}
                    className="w-full rounded-lg border border-border bg-card text-foreground px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 font-mono"
                  />
                </div>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={submitting || !userId.trim() || !description.trim()}
              className="w-full inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
              {submitting ? "Submitting..." : "Submit Report"}
            </button>
          </form>

          {/* Submission Error */}
          {submitError && (
            <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/5 p-4">
              <p className="text-red-700 font-medium text-sm">
                Submission Failed
              </p>
              <p className="text-muted-foreground text-sm mt-1">
                {submitError}
              </p>
            </div>
          )}

          {/* Submission Success */}
          {submitResult && (
            <div className="mt-4 rounded-lg border border-green-500/30 bg-green-500/5 p-4">
              <div className="flex items-center gap-2 mb-2">
                <Star className="w-4 h-4 text-green-700" />
                <p className="text-green-700 font-medium text-sm">
                  Report Submitted Successfully!
                </p>
              </div>
              <div className="grid grid-cols-2 gap-3 mt-3">
                <div className="bg-green-500/10 rounded-lg p-3 text-center">
                  <p className="text-xs text-muted-foreground">
                    Points Earned
                  </p>
                  <p className="text-2xl font-bold text-green-700 mt-0.5">
                    +{submitResult.points_awarded}
                  </p>
                </div>
                <div className="bg-green-500/10 rounded-lg p-3 text-center">
                  <p className="text-xs text-muted-foreground">Report ID</p>
                  <p className="text-sm font-mono text-foreground mt-1">
                    {submitResult.report_id}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ═══════════════════════════════════════════════════
            Leaderboard
            ═══════════════════════════════════════════════════ */}
        <div className="bg-card rounded-lg border border-border p-5">
          <h2 className="text-sm font-medium text-muted-foreground mb-4 flex items-center gap-2">
            <Users className="w-4 h-4" />
            Leaderboard
          </h2>

          {/* Loading */}
          {lbLoading && (
            <div className="flex items-center justify-center gap-2 text-muted-foreground text-sm py-12">
              <RefreshCw className="w-4 h-4 animate-spin" />
              Loading leaderboard...
            </div>
          )}

          {/* Error */}
          {lbError && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-4">
              <p className="text-red-700 font-medium text-sm">
                Failed to load leaderboard
              </p>
              <p className="text-muted-foreground text-sm mt-1">{lbError}</p>
            </div>
          )}

          {/* Empty */}
          {!lbLoading && !lbError && leaderboard.length === 0 && (
            <div className="py-12 text-center">
              <Trophy className="w-8 h-8 text-muted-foreground/40 mx-auto mb-2" />
              <p className="text-muted-foreground text-sm">
                No leaderboard data yet. Be the first to submit a report!
              </p>
            </div>
          )}

          {/* Leaderboard Table */}
          {!lbLoading && !lbError && leaderboard.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left">
                    <th className="pb-3 text-xs font-medium text-muted-foreground w-12">
                      Rank
                    </th>
                    <th className="pb-3 text-xs font-medium text-muted-foreground">
                      Name
                    </th>
                    <th className="pb-3 text-xs font-medium text-muted-foreground">
                      City
                    </th>
                    <th className="pb-3 text-xs font-medium text-muted-foreground text-right">
                      Points
                    </th>
                    <th className="pb-3 text-xs font-medium text-muted-foreground text-center">
                      Level
                    </th>
                    <th className="pb-3 text-xs font-medium text-muted-foreground">
                      Title
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {leaderboard.map((entry, idx) => (
                    <tr
                      key={entry.user_id}
                      className={`border-b border-border/50 hover:bg-muted/20 transition-colors ${
                        idx < 3 ? "bg-primary/5" : ""
                      }`}
                    >
                      <td className="py-3 pr-2">
                        <div className="flex items-center justify-center">
                          {rankIcon(entry.rank)}
                        </div>
                      </td>
                      <td className="py-3">
                        <span className="font-medium text-foreground">
                          {entry.username}
                        </span>
                      </td>
                      <td className="py-3">
                        <span className="text-muted-foreground text-xs">
                          {entry.city}
                        </span>
                      </td>
                      <td className="py-3 text-right">
                        <span className="font-mono font-bold text-primary">
                          {entry.eco_points.toLocaleString()}
                        </span>
                      </td>
                      <td className="py-3 text-center">
                        <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-primary/10 text-primary text-xs font-bold">
                          {entry.level}
                        </span>
                      </td>
                      <td className="py-3">
                        <span className="text-muted-foreground text-xs">
                          {getLevelName(entry.level)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
