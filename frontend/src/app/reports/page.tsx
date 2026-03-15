"use client";

import { useEffect, useState } from "react";
import {
  downloadCityReport,
  downloadStateReport,
  downloadNationalReport,
  getAvailableCities,
  getAvailableStates,
} from "@/lib/api";
import {
  FileDown,
  Loader2,
  FileText,
  Building2,
  MapPin,
  Globe,
  CheckSquare,
  Square,
} from "lucide-react";

type ReportScope = "city" | "state" | "national";

export default function ReportsPage() {
  const [scope, setScope] = useState<ReportScope>("national");
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [cities, setCities] = useState<string[]>([]);
  const [states, setStates] = useState<string[]>([]);
  const [includeAqi, setIncludeAqi] = useState(true);
  const [includeWater, setIncludeWater] = useState(true);
  const [includeNoise, setIncludeNoise] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [citiesLoading, setCitiesLoading] = useState(false);
  const [statesLoading, setStatesLoading] = useState(false);

  // Load available cities and states
  useEffect(() => {
    setCitiesLoading(true);
    setStatesLoading(true);
    getAvailableCities()
      .then((data) => setCities(data.cities))
      .catch(() => {})
      .finally(() => setCitiesLoading(false));
    getAvailableStates()
      .then((data) => setStates(data.states))
      .catch(() => {})
      .finally(() => setStatesLoading(false));
  }, []);

  const handleDownload = async () => {
    if (scope === "city" && !city) {
      setError("Please select a city.");
      return;
    }
    if (scope === "state" && !state) {
      setError("Please select a state.");
      return;
    }
    if (!includeAqi && !includeWater && !includeNoise) {
      setError("Please select at least one section to include.");
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const params = {
        include_aqi: includeAqi,
        include_water: includeWater,
        include_noise: includeNoise,
      };

      let blob: Blob;
      let filename: string;
      const dateStr = new Date().toISOString().slice(0, 10);

      if (scope === "city") {
        blob = await downloadCityReport(city, params);
        filename = `PrithviNET_Report_City_${city.replace(/\s+/g, "_")}_${dateStr}.pdf`;
      } else if (scope === "state") {
        blob = await downloadStateReport(state, params);
        filename = `PrithviNET_Report_State_${state.replace(/\s+/g, "_")}_${dateStr}.pdf`;
      } else {
        blob = await downloadNationalReport(params);
        filename = `PrithviNET_Report_National_${dateStr}.pdf`;
      }

      // Trigger download
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      setSuccess(`Report generated successfully: ${filename}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Report generation failed.");
    } finally {
      setLoading(false);
    }
  };

  const SectionCheckbox = ({
    label,
    checked,
    onChange,
    color,
  }: {
    label: string;
    checked: boolean;
    onChange: (v: boolean) => void;
    color: string;
  }) => (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`flex items-center gap-2 px-4 py-3 rounded-lg border transition-colors text-sm font-medium ${
        checked
          ? "border-current bg-opacity-10"
          : "border-border text-muted-foreground"
      }`}
      style={
        checked
          ? { color, backgroundColor: `${color}10`, borderColor: `${color}40` }
          : undefined
      }
    >
      {checked ? (
        <CheckSquare className="w-4 h-4" />
      ) : (
        <Square className="w-4 h-4" />
      )}
      {label}
    </button>
  );

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      {/* Page Header */}
      <div>
        <div className="flex items-center gap-3 mb-1">
          <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center">
            <FileText className="w-5 h-5 text-green-700" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-foreground">
              Report Generation
            </h1>
            <p className="text-sm text-muted-foreground">
              Generate official environmental monitoring reports in PDF format
            </p>
          </div>
        </div>
      </div>

      {/* Report Scope Selection */}
      <div className="bg-card border border-border rounded-lg p-5 space-y-4">
        <h2 className="text-sm font-semibold text-foreground uppercase tracking-wide">
          Report Scope
        </h2>
        <div className="grid grid-cols-3 gap-3">
          {(
            [
              { key: "national", label: "National", icon: Globe, desc: "All India (591 stations)" },
              { key: "state", label: "State", icon: Building2, desc: "State-level report" },
              { key: "city", label: "City", icon: MapPin, desc: "City-level report" },
            ] as const
          ).map((opt) => (
            <button
              key={opt.key}
              onClick={() => {
                setScope(opt.key);
                setError(null);
              }}
              className={`flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-colors text-sm ${
                scope === opt.key
                  ? "border-green-600 bg-green-500/5 text-green-800"
                  : "border-border text-muted-foreground hover:border-green-600/30"
              }`}
            >
              <opt.icon className="w-6 h-6" />
              <span className="font-semibold">{opt.label}</span>
              <span className="text-xs opacity-70">{opt.desc}</span>
            </button>
          ))}
        </div>

        {/* City selector */}
        {scope === "city" && (
          <div className="space-y-1">
            <label className="text-sm font-medium text-foreground">
              Select City
            </label>
            {citiesLoading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                Loading cities...
              </div>
            ) : (
              <select
                value={city}
                onChange={(e) => {
                  setCity(e.target.value);
                  setError(null);
                }}
                className="w-full px-3 py-2 rounded-lg border border-border bg-card text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-green-600"
              >
                <option value="">-- Select a city --</option>
                {cities.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            )}
          </div>
        )}

        {/* State selector */}
        {scope === "state" && (
          <div className="space-y-1">
            <label className="text-sm font-medium text-foreground">
              Select State
            </label>
            {statesLoading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                Loading states...
              </div>
            ) : (
              <select
                value={state}
                onChange={(e) => {
                  setState(e.target.value);
                  setError(null);
                }}
                className="w-full px-3 py-2 rounded-lg border border-border bg-card text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-green-600"
              >
                <option value="">-- Select a state --</option>
                {states.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            )}
          </div>
        )}
      </div>

      {/* Sections to Include */}
      <div className="bg-card border border-border rounded-lg p-5 space-y-4">
        <h2 className="text-sm font-semibold text-foreground uppercase tracking-wide">
          Sections to Include
        </h2>
        <div className="flex gap-3 flex-wrap">
          <SectionCheckbox
            label="Air Quality (AQI)"
            checked={includeAqi}
            onChange={setIncludeAqi}
            color="#009966"
          />
          <SectionCheckbox
            label="Water Quality (WQI)"
            checked={includeWater}
            onChange={setIncludeWater}
            color="#0571b0"
          />
          <SectionCheckbox
            label="Noise Monitoring"
            checked={includeNoise}
            onChange={setIncludeNoise}
            color="#8b5cf6"
          />
        </div>
      </div>

      {/* Generate Button */}
      <button
        onClick={handleDownload}
        disabled={loading}
        className="w-full flex items-center justify-center gap-2 px-6 py-3.5 rounded-lg text-white font-semibold transition-colors disabled:opacity-60 disabled:cursor-wait"
        style={{ backgroundColor: loading ? "#6b7280" : "#005032" }}
      >
        {loading ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            Generating Report...
          </>
        ) : (
          <>
            <FileDown className="w-5 h-5" />
            Generate & Download PDF Report
          </>
        )}
      </button>

      {/* Error / Success messages */}
      {error && (
        <div className="px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
          {error}
        </div>
      )}
      {success && (
        <div className="px-4 py-3 rounded-lg bg-green-50 border border-green-200 text-green-700 text-sm">
          {success}
        </div>
      )}

      {/* Report Contents Preview */}
      <div className="bg-card border border-border rounded-lg p-5 space-y-3">
        <h2 className="text-sm font-semibold text-foreground uppercase tracking-wide">
          Report Contents
        </h2>
        <div className="text-sm text-muted-foreground space-y-2">
          <p>
            The generated PDF report follows the official CPCB government format
            and includes:
          </p>
          <ul className="list-disc list-inside space-y-1 ml-2">
            {includeAqi && (
              <>
                <li>AQI summary with station-wise readings</li>
                <li>
                  AQI category distribution (Good/Satisfactory/Moderate/Poor/Very
                  Poor/Severe)
                </li>
                <li>Pollutant concentrations vs NAAQS limits</li>
                {scope !== "city" && (
                  <li>City-wise average AQI ranking</li>
                )}
              </>
            )}
            {includeWater && (
              <>
                <li>Water Quality Index (WQI) distribution</li>
                <li>Stations requiring attention (lowest WQI)</li>
                <li>BIS standard violations by parameter</li>
              </>
            )}
            {includeNoise && (
              <>
                <li>CPCB Noise Standards 2000 reference</li>
                <li>Zone-wise compliance summary</li>
                <li>Station-wise noise levels (loudest first)</li>
              </>
            )}
            <li>Annexure: NAAQS standards, AQI breakpoints, methodology</li>
          </ul>
          <p className="text-xs mt-3 text-muted-foreground/70">
            Data sourced from CPCB CAAQMS, NANMN, data.gov.in | Report
            generated by PrithviNET v1.0
          </p>
        </div>
      </div>
    </div>
  );
}
