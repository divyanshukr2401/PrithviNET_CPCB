"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { getLiveAir, getStations } from "@/lib/api";
import type { AirReading } from "@/lib/types";
import { getAQICategory } from "@/lib/types";
import { AQIMap } from "@/components/aqi-map";
import {
  StatsCards,
  AQICategoryBadges,
  StationDetailPanel,
  StationList,
  AQIColorLegend,
} from "@/components/charts";
import { RefreshCw, Radio, Search } from "lucide-react";

export default function DashboardPage() {
  const [readings, setReadings] = useState<AirReading[]>([]);
  const [stationNameMap, setStationNameMap] = useState<Record<string, string>>({});
  const [stationStateMap, setStationStateMap] = useState<Record<string, string>>({});
  const [allStates, setAllStates] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [selectedStation, setSelectedStation] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedState, setSelectedState] = useState("");

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
      .catch(() => {
        // Non-critical — station names just won't show
      });
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

  // Auto-refresh every 30 seconds
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchData]);

  // Filter readings based on search query and state
  const filteredReadings = useMemo(() => {
    if (!searchQuery && !selectedState) return readings;
    const q = searchQuery.toLowerCase();
    // Build set of station IDs that match filters
    const matchingStationIds = new Set<string>();
    readings.forEach((r) => {
      if (r.parameter !== "AQI") return; // Check filter against AQI readings only
      const name = (stationNameMap[r.station_id] || "").toLowerCase();
      const city = (r.city || "").toLowerCase();
      const state = (stationStateMap[r.station_id] || "").toLowerCase();

      const matchesSearch = !q || name.includes(q) || city.includes(q) || r.station_id.toLowerCase().includes(q);
      const matchesState = !selectedState || state === selectedState.toLowerCase();

      if (matchesSearch && matchesState) {
        matchingStationIds.add(r.station_id);
      }
    });
    return readings.filter((r) => matchingStationIds.has(r.station_id));
  }, [readings, searchQuery, selectedState, stationNameMap, stationStateMap]);

  const handleStationClick = (stationId: string) => {
    setSelectedStation(stationId === selectedStation ? null : stationId);
  };

  if (loading) {
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

  if (error) {
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

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold">National Air Quality Index</h1>
          <p className="text-muted-foreground text-sm mt-0.5">
            Real-time CPCB station monitoring across India
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Radio className="w-3 h-3 text-green-400 animate-pulse-dot" />
            <span>
              Live{lastUpdate ? ` | ${lastUpdate.toLocaleTimeString()}` : ""}
            </span>
          </div>
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`px-3 py-1.5 rounded-lg text-xs border transition-colors ${
              autoRefresh
                ? "border-green-500/30 text-green-400 bg-green-500/10"
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
      </div>

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
            Showing {aqiReadings.length} of {totalAqiReadings.length} stations
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

      {/* Map + Station Detail/List — CPCB layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Map — left side */}
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

        {/* Right side — Station Detail or Station List */}
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

      {/* AQI Color Code Legend (like CPCB bottom table) */}
      <div className="bg-card rounded-lg border border-border p-4">
        <h3 className="text-sm font-medium text-muted-foreground mb-3">
          AQI Color Code
        </h3>
        <AQIColorLegend />
      </div>
    </div>
  );
}
