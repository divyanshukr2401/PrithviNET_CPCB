"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { getLiveAir, getStations, getWaterQualityHeatmap } from "@/lib/api";
import type { AirReading, WaterQualityHeatmapPoint } from "@/lib/types";
import { getAQICategory } from "@/lib/types";
import { AQIMap } from "@/components/aqi-map";
import { WaterQualityMap } from "@/components/water-quality-map";
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
            <div className="lg:col-span-5 bg-card rounded-lg border border-border overflow-hidden">
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
                className="h-[500px]"
              />
            </div>

            <div className="lg:col-span-7 bg-card rounded-lg border border-border overflow-hidden flex flex-col">
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
                    maxHeight="460px"
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
          {waterLoading && (
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
          )}

          {waterError && (
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
          )}

          {waterFetched && !waterError && (
            <>
              {/* Water quality stats */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
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
                    Excellent Quality
                  </div>
                  <div className="text-2xl font-bold text-green-700">
                    {waterPoints.filter((p) => p.wqi <= 0.2).length}
                  </div>
                </div>
                <div className="bg-card rounded-lg border border-border p-4">
                  <div className="text-xs text-muted-foreground mb-1">
                    Fair Quality
                  </div>
                  <div className="text-2xl font-bold text-yellow-600">
                    {
                      waterPoints.filter(
                        (p) => p.wqi > 0.2 && p.wqi <= 0.5
                      ).length
                    }
                  </div>
                </div>
                <div className="bg-card rounded-lg border border-border p-4">
                  <div className="text-xs text-muted-foreground mb-1">
                    Poor Quality
                  </div>
                  <div className="text-2xl font-bold text-red-700">
                    {waterPoints.filter((p) => p.wqi > 0.5).length}
                  </div>
                </div>
              </div>

              {/* Heatmap */}
              <div className="bg-card rounded-lg border border-border overflow-hidden">
                <div className="p-3 border-b border-border flex items-center justify-between">
                  <h3 className="text-sm font-medium">
                    Water Quality Heatmap
                  </h3>
                  <span className="text-xs text-muted-foreground">
                    {waterPoints.length} monitoring stations | Source:
                    data.gov.in CPCB
                  </span>
                </div>
                <WaterQualityMap
                  points={waterPoints.map((p) => ({
                    lat: p.lat,
                    lng: p.lng,
                    intensity: p.intensity,
                    station_name: p.station_name,
                    state: p.state,
                    parameters: p.parameters,
                  }))}
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
                      range: "WQI 0 - 0.2",
                    },
                    {
                      label: "Good",
                      color: "#92c5de",
                      range: "WQI 0.2 - 0.35",
                    },
                    {
                      label: "Fair",
                      color: "#f7f056",
                      range: "WQI 0.35 - 0.5",
                    },
                    {
                      label: "Poor",
                      color: "#f4a582",
                      range: "WQI 0.5 - 0.75",
                    },
                    {
                      label: "Very Poor",
                      color: "#ca0020",
                      range: "WQI 0.75 - 1.0",
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
          )}
        </>
      )}

      {/* ═══════════════════════════════════════════════════════
          NOISE VIEW (Coming Soon)
          ═══════════════════════════════════════════════════════ */}
      {activeLayer === "noise" && (
        <div className="flex items-center justify-center py-20">
          <div className="text-center bg-card p-10 rounded-lg border border-border max-w-lg">
            <Volume2
              className="w-16 h-16 mx-auto mb-4"
              style={{ color: "#8b5cf6" }}
            />
            <h2 className="text-xl font-bold mb-2">
              Environmental Noise Monitoring
            </h2>
            <p className="text-muted-foreground text-sm mb-4">
              CNOSSOS-EU compliant noise mapping with real-time decibel levels
              from monitoring stations across India. This module is under
              development.
            </p>
            <div
              className="inline-block px-4 py-2 rounded-lg text-sm font-medium text-white"
              style={{ backgroundColor: "#8b5cf6" }}
            >
              Coming Soon
            </div>
            <p className="text-xs text-muted-foreground mt-4">
              Backend endpoints are wired at /api/v1/noise — awaiting data
              source integration
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
