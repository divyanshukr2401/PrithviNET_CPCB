"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { getLiveAir, getStations, getWaterQualityHeatmap, getGroundwaterLevel, getNoiseLive } from "@/lib/api";
import type { AirReading, WaterQualityHeatmapPoint, GroundwaterCity, NoiseStation, NoiseLiveResponse, DistrictNoiseData } from "@/lib/types";
import { getAQICategory, getNoiseComplianceColor, getNoiseComplianceLabel, ZONE_DISPLAY, RISK_LEVEL_COLORS, COMPLIANCE_COLORS } from "@/lib/types";
import { AQIMap } from "@/components/aqi-map";
import { NoiseMap } from "@/components/noise-map";
import { NoiseStationDetail } from "@/components/noise-station-detail";
import { DistrictNoiseMap } from "@/components/district-noise-map";
import { DistrictNoiseDetail } from "@/components/district-noise-detail";
import { WaterQualityMap } from "@/components/water-quality-map";
import {
  GroundwaterExploitationMap,
} from "@/components/groundwater-exploitation-map";
import districtNoiseRaw from "@/lib/data/district_noise_data.json";
import {
  StatsCards,
  AQICategoryBadges,
  StationDetailPanel,
  StationList,
  AQIColorLegend,
} from "@/components/charts";
import {
  RefreshCw,
  Radio,
  Search,
  ChevronDown,
  Droplets,
  Wind,
  Volume2,
} from "lucide-react";

type ActiveLayer = "aqi" | "water" | "noise";

const LAYER_CONFIG: Record<
  ActiveLayer,
  { label: string; subtitle: string; icon: typeof Wind }
> = {
  aqi: {
    label: "National Air Quality Index",
    subtitle: "Real-time CPCB station monitoring across India",
    icon: Wind,
  },
  water: {
    label: "Surface Water Quality",
    subtitle: "CPCB water quality monitoring stations across India",
    icon: Droplets,
  },
  noise: {
    label: "Environmental Noise Monitoring",
    subtitle: "CNOSSOS-EU compliant acoustic analysis",
    icon: Volume2,
  },
};

export default function DashboardPage() {
  // Layer selector state
  const [activeLayer, setActiveLayer] = useState<ActiveLayer>("aqi");
  const [dropdownOpen, setDropdownOpen] = useState(false);

  // AQI state
  const [readings, setReadings] = useState<AirReading[]>([]);
  const [stationNameMap, setStationNameMap] = useState<
    Record<string, string>
  >({});
  const [stationStateMap, setStationStateMap] = useState<
    Record<string, string>
  >({});
  const [allStates, setAllStates] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [selectedStation, setSelectedStation] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedState, setSelectedState] = useState("");

  // Water quality heatmap state
  const [waterPoints, setWaterPoints] = useState<WaterQualityHeatmapPoint[]>(
    []
  );
  const [waterLoading, setWaterLoading] = useState(false);
  const [waterError, setWaterError] = useState<string | null>(null);
  const [waterFetched, setWaterFetched] = useState(false);

  // Groundwater level search state
  const [gwCities, setGwCities] = useState<GroundwaterCity[]>([]);
  const [gwLoaded, setGwLoaded] = useState(false);
  const [gwQuery, setGwQuery] = useState("");
  const [gwSelected, setGwSelected] = useState<GroundwaterCity | null>(null);
  const [gwDropdownOpen, setGwDropdownOpen] = useState(false);

  // Noise monitoring state
  const [noiseStations, setNoiseStations] = useState<NoiseStation[]>([]);
  const [noiseLoading, setNoiseLoading] = useState(false);
  const [noiseError, setNoiseError] = useState<string | null>(null);
  const [noiseFetched, setNoiseFetched] = useState(false);
  const [noisePeriod, setNoisePeriod] = useState<string>("day");
  const [noiseExceedanceCount, setNoiseExceedanceCount] = useState(0);
  const [noiseCompliantCount, setNoiseCompliantCount] = useState(0);
  const [noiseLastUpdated, setNoiseLastUpdated] = useState<string | null>(null);
  const [selectedNoiseStation, setSelectedNoiseStation] = useState<string | null>(null);

  // Noise sub-view toggle: "live" (70 NANMN) vs "district" (285 districts)
  type NoiseSubView = "live" | "district";
  const [noiseSubView, setNoiseSubView] = useState<NoiseSubView>("district");
  const districtNoiseData: DistrictNoiseData[] = districtNoiseRaw as DistrictNoiseData[];
  const [selectedDistrictNoise, setSelectedDistrictNoise] = useState<string | null>(null);

  // Fetch station metadata (names, states) once
  useEffect(() => {
    getStations()
      .then((data) => {
        const nameMap: Record<string, string> = {};
        const stateMap: Record<string, string> = {};
        const statesSet = new Set<string>();
        data.stations.forEach((s) => {
          nameMap[s.station_id] = s.station_name;
          stateMap[s.station_id] = s.state;
          if (s.state) statesSet.add(s.state);
        });
        setStationNameMap(nameMap);
        setStationStateMap(stateMap);
        setAllStates(Array.from(statesSet).sort());
      })
      .catch(() => {});
  }, []);

  const fetchData = useCallback(async () => {
    try {
      const data = await getLiveAir({ include_pollutants: true });
      setReadings(data.readings);
      setLastUpdate(new Date());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Auto-refresh every 30 seconds (AQI only)
  useEffect(() => {
    if (!autoRefresh || activeLayer !== "aqi") return;
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchData, activeLayer]);

  // Fetch water quality data when tab first opened
  useEffect(() => {
    if (activeLayer === "water" && !waterFetched && !waterLoading) {
      setWaterLoading(true);
      getWaterQualityHeatmap({ limit: 5000 })
        .then((data) => {
          setWaterPoints(data.points);
          setWaterFetched(true);
          setWaterError(null);
        })
        .catch((err) => {
          setWaterError(
            err instanceof Error ? err.message : "Failed to fetch water data"
          );
        })
        .finally(() => setWaterLoading(false));
    }
  }, [activeLayer, waterFetched, waterLoading]);

  // Fetch groundwater city data when water tab first opened
  useEffect(() => {
    if (activeLayer === "water" && !gwLoaded) {
      getGroundwaterLevel()
        .then((data) => {
          setGwCities(data.cities);
          setGwLoaded(true);
        })
      .catch((err) => { console.warn("Groundwater level fetch failed:", err); });
    }
  }, [activeLayer, gwLoaded]);

  // Fetch noise live data when tab first opened
  useEffect(() => {
    if (activeLayer === "noise" && !noiseFetched && !noiseLoading) {
      setNoiseLoading(true);
      getNoiseLive()
        .then((data: NoiseLiveResponse) => {
          setNoiseStations(data.stations);
          setNoisePeriod(data.period);
          setNoiseExceedanceCount(data.exceedance_count);
          setNoiseCompliantCount(data.compliant_count);
          setNoiseLastUpdated(data.last_updated);
          setNoiseFetched(true);
          setNoiseError(null);
        })
        .catch((err) => {
          setNoiseError(
            err instanceof Error ? err.message : "Failed to fetch noise data"
          );
        })
        .finally(() => setNoiseLoading(false));
    }
  }, [activeLayer, noiseFetched, noiseLoading]);

  // Client-side filter for groundwater city dropdown
  const gwFiltered = useMemo(() => {
    if (!gwQuery.trim()) return [];
    const q = gwQuery.toLowerCase().trim();
    return gwCities.filter((c) => c.city.toLowerCase().includes(q)).slice(0, 8);
  }, [gwCities, gwQuery]);

  // Filter readings based on search query and state
  const filteredReadings = useMemo(() => {
    if (!searchQuery && !selectedState) return readings;
    const q = searchQuery.toLowerCase();
    const matchingStationIds = new Set<string>();
    readings.forEach((r) => {
      if (r.parameter !== "AQI") return;
      const name = (stationNameMap[r.station_id] || "").toLowerCase();
      const city = (r.city || "").toLowerCase();
      const state = (stationStateMap[r.station_id] || "").toLowerCase();
      const matchesSearch =
        !q ||
        name.includes(q) ||
        city.includes(q) ||
        r.station_id.toLowerCase().includes(q);
      const matchesState =
        !selectedState || state === selectedState.toLowerCase();
      if (matchesSearch && matchesState) {
        matchingStationIds.add(r.station_id);
      }
    });
    return readings.filter((r) => matchingStationIds.has(r.station_id));
  }, [readings, searchQuery, selectedState, stationNameMap, stationStateMap]);

  const handleStationClick = (stationId: string) => {
    setSelectedStation(stationId === selectedStation ? null : stationId);
  };

  // Loading state (initial AQI load)
  if (loading && activeLayer === "aqi") {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-primary mx-auto mb-3" />
          <p className="text-muted-foreground">
            Loading live air quality data...
          </p>
        </div>
      </div>
    );
  }

  // Error state (AQI)
  if (error && activeLayer === "aqi") {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center bg-card p-8 rounded-lg border border-border max-w-md">
          <p className="text-destructive font-medium mb-2">Connection Error</p>
          <p className="text-muted-foreground text-sm mb-4">{error}</p>
          <button
            onClick={fetchData}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm hover:bg-primary/90 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const aqiReadings = filteredReadings.filter((r) => r.parameter === "AQI");
  const totalAqiReadings = readings.filter((r) => r.parameter === "AQI");
  const currentConfig = LAYER_CONFIG[activeLayer];
  const LayerIcon = currentConfig.icon;

  return (
    <div className="space-y-5">
      {/* Header with Layer Dropdown */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          {/* 3-way dropdown selector */}
          <div className="relative">
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center gap-2 px-4 py-2.5 rounded-lg border-2 transition-colors bg-card hover:bg-muted/50"
              style={{
                borderColor:
                  activeLayer === "aqi"
                    ? "#009966"
                    : activeLayer === "water"
                    ? "#0571b0"
                    : "#8b5cf6",
              }}
            >
              <LayerIcon
                className="w-5 h-5"
                style={{
                  color:
                    activeLayer === "aqi"
                      ? "#009966"
                      : activeLayer === "water"
                      ? "#0571b0"
                      : "#8b5cf6",
                }}
              />
              <div className="text-left">
                <div className="text-lg font-bold leading-tight">
                  {currentConfig.label}
                </div>
                <div className="text-xs text-muted-foreground leading-tight">
                  {currentConfig.subtitle}
                </div>
              </div>
              <ChevronDown
                className={`w-4 h-4 ml-2 text-muted-foreground transition-transform ${
                  dropdownOpen ? "rotate-180" : ""
                }`}
              />
            </button>

            {/* Dropdown menu */}
            {dropdownOpen && (
              <div className="absolute top-full left-0 mt-1 w-full min-w-[340px] bg-card border border-border rounded-lg shadow-lg z-50 overflow-hidden">
                {(Object.entries(LAYER_CONFIG) as [ActiveLayer, typeof currentConfig][]).map(
                  ([key, config]) => {
                    const Icon = config.icon;
                    const isActive = key === activeLayer;
                    return (
                      <button
                        key={key}
                        onClick={() => {
                          setActiveLayer(key);
                          setDropdownOpen(false);
                        }}
                        className={`flex items-center gap-3 w-full px-4 py-3 text-left transition-colors ${
                          isActive
                            ? "bg-primary/10"
                            : "hover:bg-muted/50"
                        }`}
                      >
                        <Icon
                          className="w-5 h-5 flex-shrink-0"
                          style={{
                            color:
                              key === "aqi"
                                ? "#009966"
                                : key === "water"
                                ? "#0571b0"
                                : "#8b5cf6",
                          }}
                        />
                        <div>
                          <div className="text-sm font-medium">
                            {config.label}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {config.subtitle}
                          </div>
                        </div>
                        {isActive && (
                          <div
                            className="ml-auto w-2 h-2 rounded-full"
                            style={{
                              backgroundColor:
                                key === "aqi"
                                  ? "#009966"
                                  : key === "water"
                                  ? "#0571b0"
                                  : "#8b5cf6",
                            }}
                          />
                        )}
                      </button>
                    );
                  }
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right side controls — only for AQI */}
        {activeLayer === "aqi" && (
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Radio className="w-3 h-3 text-green-700 animate-pulse-dot" />
              <span>
                Live
                {lastUpdate ? ` | ${lastUpdate.toLocaleTimeString()}` : ""}
              </span>
            </div>
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`px-3 py-1.5 rounded-lg text-xs border transition-colors ${
                autoRefresh
                  ? "border-green-600/30 text-green-700 bg-green-500/10"
                  : "border-border text-muted-foreground"
              }`}
            >
              Auto-refresh {autoRefresh ? "ON" : "OFF"}
            </button>
            <button
              onClick={fetchData}
              className="p-2 rounded-lg border border-border hover:bg-muted/50 transition-colors"
              title="Refresh now"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Close dropdown on outside click */}
      {dropdownOpen && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setDropdownOpen(false)}
        />
      )}

      {/* ═══════════════════════════════════════════════════════
          AQI VIEW
          ═══════════════════════════════════════════════════════ */}
      {activeLayer === "aqi" && (
        <>
          {/* Search + State Filter */}
          <div className="flex flex-wrap gap-3 items-center">
            <div className="relative flex-1 min-w-[200px] max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search station or city..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 rounded-lg border border-border bg-card text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
            <select
              value={selectedState}
              onChange={(e) => setSelectedState(e.target.value)}
              className="px-3 py-2 rounded-lg border border-border bg-card text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="">All States</option>
              {allStates.map((state) => (
                <option key={state} value={state}>
                  {state}
                </option>
              ))}
            </select>
            {(searchQuery || selectedState) && (
              <span className="text-xs text-muted-foreground">
                Showing {aqiReadings.length} of {totalAqiReadings.length}{" "}
                stations
              </span>
            )}
          </div>

          {/* Stats Cards */}
          <StatsCards readings={filteredReadings} />

          {/* Category Distribution */}
          <div className="bg-card rounded-lg p-4 border border-border">
            <h3 className="text-sm font-medium text-muted-foreground mb-3">
              AQI Category Distribution
            </h3>
            <AQICategoryBadges readings={filteredReadings} />
          </div>

          {/* Map + Station Detail/List */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
            <div className="lg:col-span-8 bg-card rounded-lg border border-border overflow-hidden">
              <div className="p-3 border-b border-border flex items-center justify-between">
                <h3 className="text-sm font-medium">Station Map</h3>
                <span className="text-xs text-muted-foreground">
                  {aqiReadings.length} stations
                </span>
              </div>
              <AQIMap
                readings={filteredReadings}
                onStationClick={handleStationClick}
                center={[22.5, 80.0]}
                zoom={5}
                className="h-[550px]"
              />
            </div>

            <div className="lg:col-span-4 bg-card rounded-lg border border-border overflow-hidden flex flex-col">
              {selectedStation ? (
                <StationDetailPanel
                  readings={filteredReadings}
                  stationId={selectedStation}
                  stationName={stationNameMap[selectedStation]}
                  onClose={() => setSelectedStation(null)}
                />
              ) : (
                <>
                  <div className="p-3 border-b border-border flex items-center justify-between">
                    <h3 className="text-sm font-medium">
                      Stations (by AQI)
                    </h3>
                    <span className="text-xs text-muted-foreground">
                      Click a station for details
                    </span>
                  </div>
                  <StationList
                    readings={filteredReadings}
                    onStationClick={handleStationClick}
                    stationNameMap={stationNameMap}
                    selectedStationId={selectedStation}
                    maxHeight="510px"
                  />
                </>
              )}
            </div>
          </div>

          {/* AQI Color Code Legend */}
          <div className="bg-card rounded-lg border border-border p-4">
            <h3 className="text-sm font-medium text-muted-foreground mb-3">
              AQI Color Code
            </h3>
            <AQIColorLegend />
          </div>
        </>
      )}

      {/* ═══════════════════════════════════════════════════════
          WATER QUALITY VIEW
          ═══════════════════════════════════════════════════════ */}
      {activeLayer === "water" && (
        <>
          {waterLoading ? (
            <div className="flex items-center justify-center py-20">
              <div className="text-center">
                <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-3" style={{ color: "#0571b0" }} />
                <p className="text-muted-foreground">
                  Loading water quality data from data.gov.in...
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Fetching CPCB monitoring stations
                </p>
              </div>
            </div>
          ) : waterError ? (
            <div className="flex items-center justify-center py-20">
              <div className="text-center bg-card p-8 rounded-lg border border-border max-w-md">
                <p className="text-destructive font-medium mb-2">
                  Failed to Load Water Data
                </p>
                <p className="text-muted-foreground text-sm mb-4">
                  {waterError}
                </p>
                <button
                  onClick={() => {
                    setWaterFetched(false);
                    setWaterError(null);
                  }}
                  className="px-4 py-2 rounded-lg text-sm text-white transition-colors"
                  style={{ backgroundColor: "#0571b0" }}
                >
                  Retry
                </button>
              </div>
            </div>
          ) : waterFetched ? (
            <>
              {/* Water quality stats — 5 categories matching legend */}
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                <div className="bg-card rounded-lg border border-border p-4">
                  <div className="text-xs text-muted-foreground mb-1">
                    Monitoring Stations
                  </div>
                  <div className="text-2xl font-bold" style={{ color: "#0571b0" }}>
                    {waterPoints.length}
                  </div>
                </div>
                <div className="bg-card rounded-lg border border-border p-4">
                  <div className="text-xs text-muted-foreground mb-1">
                    Excellent (WQI ≤0.15)
                  </div>
                  <div className="text-2xl font-bold" style={{ color: "#0571b0" }}>
                    {waterPoints.filter((p) => p.wqi <= 0.15).length}
                  </div>
                </div>
                <div className="bg-card rounded-lg border border-border p-4">
                  <div className="text-xs text-muted-foreground mb-1">
                    Good (0.15–0.3)
                  </div>
                  <div className="text-2xl font-bold" style={{ color: "#92c5de" }}>
                    {waterPoints.filter((p) => p.wqi > 0.15 && p.wqi <= 0.3).length}
                  </div>
                </div>
                <div className="bg-card rounded-lg border border-border p-4">
                  <div className="text-xs text-muted-foreground mb-1">
                    Fair (0.3–0.5)
                  </div>
                  <div className="text-2xl font-bold" style={{ color: "#eab308" }}>
                    {waterPoints.filter((p) => p.wqi > 0.3 && p.wqi <= 0.5).length}
                  </div>
                </div>
                <div className="bg-card rounded-lg border border-border p-4">
                  <div className="text-xs text-muted-foreground mb-1">
                    Poor (0.5–0.7)
                  </div>
                  <div className="text-2xl font-bold" style={{ color: "#f4a582" }}>
                    {waterPoints.filter((p) => p.wqi > 0.5 && p.wqi <= 0.7).length}
                  </div>
                </div>
                <div className="bg-card rounded-lg border border-border p-4">
                  <div className="text-xs text-muted-foreground mb-1">
                    Very Poor ({">"}0.7)
                  </div>
                  <div className="text-2xl font-bold" style={{ color: "#ca0020" }}>
                    {waterPoints.filter((p) => p.wqi > 0.7).length}
                  </div>
                </div>
              </div>

              {/* ── Groundwater Level Search ── */}
              <div className="bg-card rounded-lg border border-border p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Droplets className="w-4 h-4" style={{ color: "#0571b0" }} />
                  <h3 className="text-sm font-medium">
                    Groundwater Level Lookup
                  </h3>
                  <span className="text-xs text-muted-foreground ml-auto">
                    49 major cities | CGWB 2018
                  </span>
                </div>

                {/* Search input */}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <input
                    type="text"
                    placeholder="Search city for groundwater level (e.g. Delhi, Chennai, Jaipur)..."
                    value={gwQuery}
                    onChange={(e) => {
                      setGwQuery(e.target.value);
                      setGwDropdownOpen(true);
                      if (!e.target.value.trim()) setGwSelected(null);
                    }}
                    onFocus={() => {
                      if (gwQuery.trim()) setGwDropdownOpen(true);
                    }}
                    className="w-full pl-9 pr-3 py-2.5 rounded-lg border border-border bg-background text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-[#0571b0]"
                  />

                  {/* Dropdown suggestions */}
                  {gwDropdownOpen && gwFiltered.length > 0 && (
                    <div className="absolute top-full left-0 right-0 mt-1 bg-card border border-border rounded-lg shadow-lg z-50 overflow-hidden max-h-60 overflow-y-auto">
                      {gwFiltered.map((city) => (
                        <button
                          key={city.city}
                          onClick={() => {
                            setGwSelected(city);
                            setGwQuery(city.city);
                            setGwDropdownOpen(false);
                          }}
                          className="flex items-center justify-between w-full px-4 py-2.5 text-left hover:bg-muted/50 transition-colors text-sm border-b border-border last:border-b-0"
                        >
                          <span className="font-medium">{city.city}</span>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">
                              {city.depth_min_mbgl ?? "?"} – {city.depth_max_mbgl ?? "?"} m
                            </span>
                            <span
                              className="text-xs font-medium px-2 py-0.5 rounded-full text-white"
                              style={{ backgroundColor: city.classification.color }}
                            >
                              {city.classification.level}
                            </span>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}

                  {gwDropdownOpen && gwQuery.trim() && gwFiltered.length === 0 && gwLoaded && (
                    <div className="absolute top-full left-0 right-0 mt-1 bg-card border border-border rounded-lg shadow-lg z-50 p-3">
                      <p className="text-sm text-muted-foreground text-center">
                        No cities found matching &quot;{gwQuery}&quot;
                      </p>
                    </div>
                  )}
                </div>

                {/* Close dropdown on outside click */}
                {gwDropdownOpen && (
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => setGwDropdownOpen(false)}
                  />
                )}

                {/* Selected city result card */}
                {gwSelected && (
                  <div className="mt-4 rounded-lg border-2 p-4" style={{ borderColor: gwSelected.classification.color + "40" }}>
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <h4 className="text-lg font-bold">{gwSelected.city}</h4>
                        <p className="text-xs text-muted-foreground">
                          {gwSelected.wells_analysed} wells analysed | Depth:{" "}
                          {gwSelected.depth_min_mbgl ?? "N/A"} – {gwSelected.depth_max_mbgl ?? "N/A"} m below ground
                        </p>
                      </div>
                      <div className="text-right">
                        <span
                          className="inline-block px-3 py-1 rounded-full text-sm font-bold text-white"
                          style={{ backgroundColor: gwSelected.classification.color }}
                        >
                          {gwSelected.classification.level}
                        </span>
                        <p className="text-xs mt-1 font-medium" style={{ color: gwSelected.classification.color }}>
                          Avg. {gwSelected.avg_depth_mbgl} m depth
                        </p>
                      </div>
                    </div>

                    <p className="text-xs text-muted-foreground mb-3">
                      {gwSelected.classification.description}
                    </p>

                    {/* Depth band distribution bar */}
                    <div className="space-y-1.5">
                      <div className="text-xs font-medium text-muted-foreground mb-1">
                        Well Depth Distribution
                      </div>
                      {/* Stacked horizontal bar */}
                      <div className="flex h-6 rounded-md overflow-hidden border border-border">
                        {gwSelected.bands.map((band, i) => {
                          if (band.percentage <= 0) return null;
                          const colors = [
                            "#0571b0", // 0-2m  — deep blue (excellent)
                            "#48a9c5", // 2-5m  — teal
                            "#92c5de", // 5-10m — light blue
                            "#f7f056", // 10-20m — yellow
                            "#f4a582", // 20-40m — orange
                            "#ca0020", // >40m  — red (critical)
                          ];
                          return (
                            <div
                              key={band.range}
                              className="flex items-center justify-center text-[10px] font-bold text-white transition-all"
                              style={{
                                width: `${band.percentage}%`,
                                backgroundColor: colors[i],
                                minWidth: band.percentage > 0 ? "18px" : "0",
                              }}
                              title={`${band.range}: ${band.count} wells (${band.percentage}%)`}
                            >
                              {band.percentage >= 8 ? `${band.percentage}%` : ""}
                            </div>
                          );
                        })}
                      </div>
                      {/* Band legend */}
                      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2">
                        {gwSelected.bands.map((band, i) => {
                          const colors = ["#0571b0", "#48a9c5", "#92c5de", "#f7f056", "#f4a582", "#ca0020"];
                          return (
                            <div key={band.range} className="flex items-center gap-1 text-xs">
                              <div
                                className="w-2.5 h-2.5 rounded-sm"
                                style={{ backgroundColor: colors[i] }}
                              />
                              <span className="text-muted-foreground">
                                {band.range}: {band.count} wells ({band.percentage}%)
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* ── Groundwater Exploitation Choropleth ── */}
              {(() => {
                return (
                  <>
                    {/* CGWB 2024-25 District Summary */}
                    <div className="grid grid-cols-3 md:grid-cols-5 gap-3">
                      <div className="bg-card rounded-lg border border-border p-4 text-center">
                        <div className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide mb-2">Total Districts</div>
                        <div className="text-3xl font-extrabold text-foreground leading-none">776</div>
                        <div className="text-[10px] text-muted-foreground mt-1">Districts</div>
                      </div>
                      <div className="bg-card rounded-lg border border-border p-4 text-center">
                        <div className="text-[11px] font-medium uppercase tracking-wide mb-2" style={{ color: "#16a34a" }}>Safe</div>
                        <div className="text-3xl font-extrabold leading-none" style={{ color: "#16a34a" }}>404</div>
                        <div className="text-[10px] text-muted-foreground mt-1">Districts</div>
                      </div>
                      <div className="bg-card rounded-lg border border-border p-4 text-center">
                        <div className="text-[11px] font-medium uppercase tracking-wide mb-2" style={{ color: "#2563eb" }}>Semi-Critical</div>
                        <div className="text-3xl font-extrabold leading-none" style={{ color: "#2563eb" }}>173</div>
                        <div className="text-[10px] text-muted-foreground mt-1">Districts</div>
                      </div>
                      <div className="bg-card rounded-lg border border-border p-4 text-center">
                        <div className="text-[11px] font-medium uppercase tracking-wide mb-2" style={{ color: "#eab308" }}>Critical</div>
                        <div className="text-3xl font-extrabold leading-none" style={{ color: "#eab308" }}>57</div>
                        <div className="text-[10px] text-muted-foreground mt-1">Districts</div>
                      </div>
                      <div className="bg-card rounded-lg border border-border p-4 text-center">
                        <div className="text-[11px] font-medium uppercase tracking-wide mb-2" style={{ color: "#dc2626" }}>Over-Exploited</div>
                        <div className="text-3xl font-extrabold leading-none" style={{ color: "#dc2626" }}>142</div>
                        <div className="text-[10px] text-muted-foreground mt-1">Districts</div>
                      </div>
                    </div>

                    <div className="bg-card rounded-lg border border-border overflow-hidden">
                      <div className="p-3 border-b border-border flex items-center justify-between">
                        <h3 className="text-sm font-medium">Groundwater Exploitation by District</h3>
                        <span className="text-xs text-muted-foreground">CGWB 2024-25 | 776 Districts across 36 States/UTs</span>
                      </div>
                      <GroundwaterExploitationMap className="h-[550px]" />
                    </div>
                  </>
                );
              })()}

              {/* Water Quality Station Map */}
              <div className="bg-card rounded-lg border border-border overflow-hidden">
                <div className="p-3 border-b border-border flex items-center justify-between">
                  <h3 className="text-sm font-medium">
                    Water Quality Station Map
                  </h3>
                  <span className="text-xs text-muted-foreground">
                    {waterPoints.length} monitoring stations | Source:
                    data.gov.in CPCB
                  </span>
                </div>
                <WaterQualityMap
                  points={waterPoints}
                  className="h-[550px]"
                />
              </div>

              {/* Water Quality Legend */}
              <div className="bg-card rounded-lg border border-border p-4">
                <h3 className="text-sm font-medium text-muted-foreground mb-3">
                  Water Quality Index (WQI) Color Scale
                </h3>
                <div className="flex flex-wrap gap-3">
                  {[
                    {
                      label: "Excellent",
                      color: "#0571b0",
                      range: "WQI 0 - 0.15",
                    },
                    {
                      label: "Good",
                      color: "#92c5de",
                      range: "WQI 0.15 - 0.3",
                    },
                    {
                      label: "Fair",
                      color: "#eab308",
                      range: "WQI 0.3 - 0.5",
                    },
                    {
                      label: "Poor",
                      color: "#f4a582",
                      range: "WQI 0.5 - 0.7",
                    },
                    {
                      label: "Very Poor",
                      color: "#ca0020",
                      range: "WQI 0.7 - 1.0",
                    },
                  ].map((item) => (
                    <div
                      key={item.label}
                      className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border"
                    >
                      <div
                        className="w-4 h-4 rounded-sm"
                        style={{ backgroundColor: item.color }}
                      />
                      <div>
                        <span className="text-sm font-medium">
                          {item.label}
                        </span>
                        <span className="text-xs text-muted-foreground ml-1">
                          ({item.range})
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground mt-3">
                  WQI is computed from BOD, coliform, conductivity, and nitrate
                  levels relative to BIS standards. Higher values indicate worse
                  water quality.
                </p>
              </div>
            </>
          ) : null}
        </>
      )}

      {/* ═══════════════════════════════════════════════════════
          NOISE VIEW
          ═══════════════════════════════════════════════════════ */}
      {activeLayer === "noise" && (
        <>
          {/* Sub-toggle: Live Monitors vs District Snapshot */}
          <div className="flex items-center gap-2">
            <div className="bg-card rounded-lg border border-border p-1 flex gap-1">
              <button
                onClick={() => { setNoiseSubView("district"); setSelectedNoiseStation(null); }}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  noiseSubView === "district"
                    ? "bg-purple-600 text-white"
                    : "text-muted-foreground hover:bg-muted/50"
                }`}
              >
                District Snapshot (285)
              </button>
              <button
                onClick={() => { setNoiseSubView("live"); setSelectedDistrictNoise(null); }}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  noiseSubView === "live"
                    ? "bg-purple-600 text-white"
                    : "text-muted-foreground hover:bg-muted/50"
                }`}
              >
                Live Monitors (70)
              </button>
            </div>
            <span className="text-xs text-muted-foreground">
              {noiseSubView === "district"
                ? "CPCB/State PCB district-wise noise data across 35 states"
                : "Real-time NANMN station monitoring across 7 cities"}
            </span>
          </div>

          {/* ─── DISTRICT SNAPSHOT SUB-VIEW ─── */}
          {noiseSubView === "district" && (
            <>
              {/* Stats Cards */}
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                <div className="bg-card rounded-lg border border-border p-3">
                  <div className="text-xs text-muted-foreground mb-1">Districts Monitored</div>
                  <div className="text-2xl font-bold">{districtNoiseData.length}</div>
                  <div className="text-[10px] text-muted-foreground">Across 35 states/UTs</div>
                </div>
                <div className="bg-card rounded-lg border border-border p-3">
                  <div className="text-xs text-muted-foreground mb-1">Critical Risk</div>
                  <div className="text-2xl font-bold" style={{ color: RISK_LEVEL_COLORS.Critical }}>
                    {districtNoiseData.filter((d) => d.risk_level === "Critical").length}
                  </div>
                  <div className="text-[10px] text-muted-foreground">Districts</div>
                </div>
                <div className="bg-card rounded-lg border border-border p-3">
                  <div className="text-xs text-muted-foreground mb-1">High Risk</div>
                  <div className="text-2xl font-bold" style={{ color: RISK_LEVEL_COLORS.High }}>
                    {districtNoiseData.filter((d) => d.risk_level === "High").length}
                  </div>
                  <div className="text-[10px] text-muted-foreground">Districts</div>
                </div>
                <div className="bg-card rounded-lg border border-border p-3">
                  <div className="text-xs text-muted-foreground mb-1">Day Violations</div>
                  <div className="text-2xl font-bold" style={{ color: "#dc2626" }}>
                    {districtNoiseData.filter((d) => d.compliance_day === "Violation").length}
                  </div>
                  <div className="text-[10px] text-muted-foreground">
                    of {districtNoiseData.length} districts
                  </div>
                </div>
                <div className="bg-card rounded-lg border border-border p-3">
                  <div className="text-xs text-muted-foreground mb-1">Night Violations</div>
                  <div className="text-2xl font-bold" style={{ color: "#dc2626" }}>
                    {districtNoiseData.filter((d) => d.compliance_night === "Violation").length}
                  </div>
                  <div className="text-[10px] text-muted-foreground">
                    of {districtNoiseData.length} districts
                  </div>
                </div>
                <div className="bg-card rounded-lg border border-border p-3">
                  <div className="text-xs text-muted-foreground mb-1">Highest Leq 24hr</div>
                  <div className="text-2xl font-bold" style={{ color: "#dc2626" }}>
                    {Math.max(...districtNoiseData.map((d) => d.leq_24hr_dba)).toFixed(1)}
                  </div>
                  <div className="text-[10px] text-muted-foreground">dB(A)</div>
                </div>
              </div>

              {/* Risk + Zone Distribution */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="bg-card rounded-lg p-4 border border-border">
                  <h3 className="text-sm font-medium text-muted-foreground mb-3">
                    Risk Level Distribution
                  </h3>
                  <div className="flex flex-wrap gap-3">
                    {(["Critical", "High", "Moderate", "Low"] as const).map((level) => {
                      const count = districtNoiseData.filter((d) => d.risk_level === level).length;
                      const pct = ((count / districtNoiseData.length) * 100).toFixed(0);
                      return (
                        <div
                          key={level}
                          className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border"
                        >
                          <span
                            className="w-3 h-3 rounded-full flex-shrink-0"
                            style={{ backgroundColor: RISK_LEVEL_COLORS[level] }}
                          />
                          <div>
                            <span className="text-sm font-medium">{level}</span>
                            <span className="text-xs text-muted-foreground ml-1.5">
                              {count} ({pct}%)
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
                <div className="bg-card rounded-lg p-4 border border-border">
                  <h3 className="text-sm font-medium text-muted-foreground mb-3">
                    Zone Type Distribution
                  </h3>
                  <div className="flex flex-wrap gap-3">
                    {Object.entries(ZONE_DISPLAY).map(([key, { label, color }]) => {
                      const count = districtNoiseData.filter(
                        (d) => d.zone_type.toLowerCase() === key
                      ).length;
                      const violations = districtNoiseData.filter(
                        (d) =>
                          d.zone_type.toLowerCase() === key &&
                          d.compliance_day === "Violation"
                      ).length;
                      return (
                        <div
                          key={key}
                          className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border"
                        >
                          <span
                            className="w-3 h-3 rounded-full flex-shrink-0"
                            style={{ backgroundColor: color }}
                          />
                          <div>
                            <span className="text-sm font-medium">{label}</span>
                            <span className="text-xs text-muted-foreground ml-1.5">
                              {count}
                            </span>
                            {violations > 0 && (
                              <span className="text-xs ml-1.5" style={{ color: "#dc2626" }}>
                                ({violations} violating)
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Map + District Detail */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
                <div className="lg:col-span-8 bg-card rounded-lg border border-border overflow-hidden">
                  <div className="p-3 border-b border-border flex items-center justify-between">
                    <h3 className="text-sm font-medium">District Noise Map</h3>
                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                        {(["Critical", "High", "Moderate", "Low"] as const).map((level) => (
                          <span key={level} className="flex items-center gap-1">
                            <span
                              className="w-2 h-2 rounded-full"
                              style={{ backgroundColor: RISK_LEVEL_COLORS[level] }}
                            />
                            {level}
                          </span>
                        ))}
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {districtNoiseData.length} districts
                      </span>
                    </div>
                  </div>
                  <DistrictNoiseMap
                    districts={districtNoiseData}
                    onDistrictClick={(id) =>
                      setSelectedDistrictNoise(id === selectedDistrictNoise ? null : id)
                    }
                    selectedDistrictId={selectedDistrictNoise}
                    center={[22.5, 80.0]}
                    zoom={5}
                    className="h-[550px]"
                  />
                </div>

                <div className="lg:col-span-4 bg-card rounded-lg border border-border overflow-hidden flex flex-col">
                  {selectedDistrictNoise &&
                  districtNoiseData.find((d) => d.district_id === selectedDistrictNoise) ? (
                    <DistrictNoiseDetail
                      district={
                        districtNoiseData.find(
                          (d) => d.district_id === selectedDistrictNoise
                        )!
                      }
                      onClose={() => setSelectedDistrictNoise(null)}
                    />
                  ) : (
                    <>
                      <div className="p-3 border-b border-border flex items-center justify-between">
                        <h3 className="text-sm font-medium">Districts (by Leq 24hr)</h3>
                        <span className="text-xs text-muted-foreground">
                          Click a district for details
                        </span>
                      </div>
                      <div className="overflow-y-auto" style={{ maxHeight: "510px" }}>
                        {[...districtNoiseData]
                          .sort((a, b) => b.leq_24hr_dba - a.leq_24hr_dba)
                          .map((d) => {
                            const riskCol = RISK_LEVEL_COLORS[d.risk_level] || "#6b7280";
                            const zoneConf = ZONE_DISPLAY[d.zone_type.toLowerCase()] || {
                              label: d.zone_type,
                              color: "#6b7280",
                            };
                            return (
                              <button
                                key={d.district_id}
                                onClick={() => setSelectedDistrictNoise(d.district_id)}
                                className="w-full text-left px-3 py-2 border-b border-border hover:bg-muted/30 transition-colors flex items-center gap-2"
                              >
                                <span
                                  className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                                  style={{ backgroundColor: riskCol }}
                                />
                                <div className="min-w-0 flex-1">
                                  <div className="text-xs font-medium truncate">
                                    {d.city_town}
                                  </div>
                                  <div className="text-[10px] text-muted-foreground truncate">
                                    {d.district}, {d.state} &middot;{" "}
                                    <span style={{ color: zoneConf.color }}>
                                      {zoneConf.label}
                                    </span>
                                  </div>
                                </div>
                                <div className="text-right flex-shrink-0">
                                  <div
                                    className="text-sm font-bold"
                                    style={{ color: riskCol }}
                                  >
                                    {d.leq_24hr_dba}
                                  </div>
                                  <div className="text-[10px] text-muted-foreground">
                                    dB(A)
                                  </div>
                                </div>
                              </button>
                            );
                          })}
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* CPCB Standards + Decibel Scale (shared) */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                <div className="bg-card rounded-lg border border-border p-4">
                  <h3 className="text-sm font-medium text-muted-foreground mb-3">
                    CPCB Noise Standards (Ambient)
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border">
                          <th className="text-left py-2 px-2 text-xs font-medium text-muted-foreground">Zone</th>
                          <th className="text-center py-2 px-2 text-xs font-medium text-muted-foreground">Day Limit</th>
                          <th className="text-center py-2 px-2 text-xs font-medium text-muted-foreground">Night Limit</th>
                        </tr>
                      </thead>
                      <tbody>
                        {[
                          { zone: "Industrial", day: 75, night: 70 },
                          { zone: "Commercial", day: 65, night: 55 },
                          { zone: "Residential", day: 55, night: 45 },
                          { zone: "Silence", day: 50, night: 40 },
                        ].map((row) => {
                          const zoneKey = row.zone.toLowerCase();
                          const zoneConf = ZONE_DISPLAY[zoneKey] || { color: "#6b7280" };
                          return (
                            <tr key={row.zone} className="border-b border-border/50">
                              <td className="py-2 px-2 flex items-center gap-1.5">
                                <span
                                  className="w-2.5 h-2.5 rounded-full"
                                  style={{ backgroundColor: zoneConf.color }}
                                />
                                <span className="font-medium text-xs">{row.zone}</span>
                              </td>
                              <td className="py-2 px-2 text-center text-xs">{row.day} dB(A)</td>
                              <td className="py-2 px-2 text-center text-xs">{row.night} dB(A)</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                  <p className="text-[10px] text-muted-foreground mt-2">
                    Day: 6:00 AM – 10:00 PM &nbsp;|&nbsp; Night: 10:00 PM – 6:00 AM
                  </p>
                  <p className="text-[10px] text-muted-foreground mt-1">
                    Source: CPCB Noise Pollution (Regulation and Control) Rules, 2000
                  </p>
                </div>
                <div className="bg-card rounded-lg border border-border p-4">
                  <h3 className="text-sm font-medium text-muted-foreground mb-3">
                    Decibel Scale Reference
                  </h3>
                  <div className="space-y-1.5">
                    {[
                      { db: 30, label: "Whisper", color: "#16a34a" },
                      { db: 40, label: "Library", color: "#16a34a" },
                      { db: 50, label: "Moderate rainfall", color: "#22c55e" },
                      { db: 60, label: "Normal conversation", color: "#eab308" },
                      { db: 70, label: "Vacuum cleaner", color: "#f97316" },
                      { db: 80, label: "Heavy traffic", color: "#ef4444" },
                      { db: 90, label: "Lawn mower", color: "#dc2626" },
                      { db: 100, label: "Motorcycle", color: "#dc2626" },
                      { db: 110, label: "Rock concert", color: "#991b1b" },
                      { db: 120, label: "Jet engine (nearby)", color: "#7f1d1d" },
                    ].map((item) => (
                      <div key={item.db} className="flex items-center gap-2">
                        <div
                          className="h-3 rounded-sm"
                          style={{
                            width: `${Math.max(10, (item.db / 120) * 100)}%`,
                            backgroundColor: item.color,
                            opacity: 0.7,
                          }}
                        />
                        <span className="text-xs font-medium whitespace-nowrap">
                          {item.db} dB
                        </span>
                        <span className="text-[10px] text-muted-foreground whitespace-nowrap">
                          {item.label}
                        </span>
                      </div>
                    ))}
                  </div>
                  <p className="text-[10px] text-muted-foreground mt-3">
                    Prolonged exposure above 85 dB(A) can cause hearing damage.
                    CPCB ambient standards apply to area-wide noise, not point-source.
                  </p>
                </div>
              </div>

              <p className="text-xs text-muted-foreground text-right">
                Sources: CPCB NANMN | MPCB 2024 | UNEP Frontiers 2022 | State PCBs | Peer-reviewed Research
              </p>
            </>
          )}

          {/* ─── LIVE MONITORS SUB-VIEW ─── */}
          {noiseSubView === "live" && (
            <>
              {noiseLoading ? (
                <div className="flex items-center justify-center py-20">
                  <div className="text-center">
                    <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-3" style={{ color: "#8b5cf6" }} />
                    <p className="text-muted-foreground">
                      Loading noise monitoring data...
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Fetching 70 NANMN stations across 7 cities
                    </p>
                  </div>
                </div>
              ) : noiseError ? (
                <div className="flex items-center justify-center py-20">
                  <div className="text-center bg-card p-8 rounded-lg border border-border max-w-md">
                    <p className="text-destructive font-medium mb-2">
                      Failed to Load Noise Data
                    </p>
                    <p className="text-muted-foreground text-sm mb-4">
                      {noiseError}
                    </p>
                    <button
                      onClick={() => {
                        setNoiseFetched(false);
                        setNoiseError(null);
                      }}
                      className="px-4 py-2 rounded-lg text-sm text-white transition-colors"
                      style={{ backgroundColor: "#8b5cf6" }}
                    >
                      Retry
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  {/* Stats Cards */}
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                    <div className="bg-card rounded-lg border border-border p-3">
                      <div className="text-xs text-muted-foreground mb-1">Active Monitors</div>
                      <div className="text-2xl font-bold">{noiseStations.length}</div>
                      <div className="text-[10px] text-muted-foreground">NANMN Stations</div>
                    </div>
                    <div className="bg-card rounded-lg border border-border p-3">
                      <div className="text-xs text-muted-foreground mb-1">Highest Noise</div>
                      <div className="text-2xl font-bold" style={{ color: "#dc2626" }}>
                        {noiseStations.length > 0
                          ? Math.max(...noiseStations.map((s) => s.leq)).toFixed(1)
                          : "—"}
                      </div>
                      <div className="text-[10px] text-muted-foreground">dB(A) Leq</div>
                    </div>
                    <div className="bg-card rounded-lg border border-border p-3">
                      <div className="text-xs text-muted-foreground mb-1">Exceedances</div>
                      <div className="text-2xl font-bold" style={{ color: "#dc2626" }}>
                        {noiseExceedanceCount}
                      </div>
                      <div className="text-[10px] text-muted-foreground">Above CPCB limit</div>
                    </div>
                    <div className="bg-card rounded-lg border border-border p-3">
                      <div className="text-xs text-muted-foreground mb-1">Compliant</div>
                      <div className="text-2xl font-bold" style={{ color: "#16a34a" }}>
                        {noiseCompliantCount}
                      </div>
                      <div className="text-[10px] text-muted-foreground">Within limits</div>
                    </div>
                    <div className="bg-card rounded-lg border border-border p-3">
                      <div className="text-xs text-muted-foreground mb-1">Period</div>
                      <div className="text-2xl font-bold capitalize">{noisePeriod}</div>
                      <div className="text-[10px] text-muted-foreground">
                        {noisePeriod === "night" ? "10 PM – 6 AM" : "6 AM – 10 PM"}
                      </div>
                    </div>
                    <div className="bg-card rounded-lg border border-border p-3">
                      <div className="text-xs text-muted-foreground mb-1">Avg Noise</div>
                      <div className="text-2xl font-bold">
                        {noiseStations.length > 0
                          ? (
                              noiseStations.reduce((sum, s) => sum + s.leq, 0) /
                              noiseStations.length
                            ).toFixed(1)
                          : "—"}
                      </div>
                      <div className="text-[10px] text-muted-foreground">dB(A) across all</div>
                    </div>
                  </div>

                  {/* Zone Distribution */}
                  <div className="bg-card rounded-lg p-4 border border-border">
                    <h3 className="text-sm font-medium text-muted-foreground mb-3">
                      Station Distribution by Zone
                    </h3>
                    <div className="flex flex-wrap gap-3">
                      {Object.entries(ZONE_DISPLAY).map(([key, { label, color }]) => {
                        const count = noiseStations.filter((s) => s.zone === key).length;
                        const exceedCount = noiseStations.filter(
                          (s) => s.zone === key && s.is_exceedance
                        ).length;
                        return (
                          <div
                            key={key}
                            className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border"
                          >
                            <span
                              className="w-3 h-3 rounded-full flex-shrink-0"
                              style={{ backgroundColor: color }}
                            />
                            <div>
                              <span className="text-sm font-medium">{label}</span>
                              <span className="text-xs text-muted-foreground ml-1.5">
                                {count} stations
                              </span>
                              {exceedCount > 0 && (
                                <span className="text-xs ml-1.5" style={{ color: "#dc2626" }}>
                                  ({exceedCount} exceeding)
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Map + Station Detail */}
                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
                    <div className="lg:col-span-8 bg-card rounded-lg border border-border overflow-hidden">
                      <div className="p-3 border-b border-border flex items-center justify-between">
                        <h3 className="text-sm font-medium">Noise Monitoring Map</h3>
                        <div className="flex items-center gap-3">
                          <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                            <span className="flex items-center gap-1">
                              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: "#16a34a" }} />
                              Compliant
                            </span>
                            <span className="flex items-center gap-1">
                              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: "#eab308" }} />
                              Warning
                            </span>
                            <span className="flex items-center gap-1">
                              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: "#dc2626" }} />
                              Exceeding
                            </span>
                          </div>
                          <span className="text-xs text-muted-foreground">
                            {noiseStations.length} stations
                          </span>
                        </div>
                      </div>
                      <NoiseMap
                        stations={noiseStations}
                        onStationClick={(id) =>
                          setSelectedNoiseStation(id === selectedNoiseStation ? null : id)
                        }
                        selectedStationId={selectedNoiseStation}
                        center={[22.5, 80.0]}
                        zoom={5}
                        className="h-[550px]"
                      />
                    </div>

                    <div className="lg:col-span-4 bg-card rounded-lg border border-border overflow-hidden flex flex-col">
                      {selectedNoiseStation && noiseStations.find((s) => s.station_id === selectedNoiseStation) ? (
                        <NoiseStationDetail
                          station={noiseStations.find((s) => s.station_id === selectedNoiseStation)!}
                          onClose={() => setSelectedNoiseStation(null)}
                        />
                      ) : (
                        <>
                          <div className="p-3 border-b border-border flex items-center justify-between">
                            <h3 className="text-sm font-medium">Stations (by noise level)</h3>
                            <span className="text-xs text-muted-foreground">
                              Click a station for details
                            </span>
                          </div>
                          <div className="overflow-y-auto" style={{ maxHeight: "510px" }}>
                            {[...noiseStations]
                              .sort((a, b) => b.leq - a.leq)
                              .map((station) => {
                                const color = getNoiseComplianceColor(station.leq, station.active_limit);
                                const zone = ZONE_DISPLAY[station.zone] || {
                                  label: station.zone,
                                  color: "#6b7280",
                                };
                                return (
                                  <button
                                    key={station.station_id}
                                    onClick={() => setSelectedNoiseStation(station.station_id)}
                                    className="w-full text-left px-3 py-2 border-b border-border hover:bg-muted/30 transition-colors flex items-center gap-2"
                                  >
                                    <span
                                      className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                                      style={{ backgroundColor: color }}
                                    />
                                    <div className="min-w-0 flex-1">
                                      <div className="text-xs font-medium truncate">
                                        {station.station_name}
                                      </div>
                                      <div className="text-[10px] text-muted-foreground truncate">
                                        {station.city} &middot;{" "}
                                        <span style={{ color: zone.color }}>{zone.label}</span>
                                      </div>
                                    </div>
                                    <div className="text-right flex-shrink-0">
                                      <div className="text-sm font-bold" style={{ color }}>
                                        {station.leq}
                                      </div>
                                      <div className="text-[10px] text-muted-foreground">
                                        dB(A)
                                      </div>
                                    </div>
                                  </button>
                                );
                              })}
                          </div>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Last updated */}
                  {noiseLastUpdated && (
                    <p className="text-xs text-muted-foreground text-right">
                      Data as of {new Date(noiseLastUpdated).toLocaleString()}
                    </p>
                  )}
                </>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
