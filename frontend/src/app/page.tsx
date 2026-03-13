"use client";

import { useEffect, useState, useCallback } from "react";
import { getLiveAir } from "@/lib/api";
import type { AirReading } from "@/lib/types";
import { AQIMap } from "@/components/aqi-map";
import {
  StatsCards,
  AQICategoryBadges,
  PollutantChart,
  StationList,
} from "@/components/charts";
import { RefreshCw, Radio } from "lucide-react";

export default function DashboardPage() {
  const [readings, setReadings] = useState<AirReading[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [selectedStation, setSelectedStation] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

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

  const aqiReadings = readings.filter((r) => r.parameter === "AQI");
  const selectedCity = selectedStation
    ? aqiReadings.find((r) => r.station_id === selectedStation)?.city
    : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Air Quality Dashboard</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Real-time CPCB station monitoring across India
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Radio className="w-3 h-3 text-green-400 animate-pulse-dot" />
            <span>
              Live{" "}
              {lastUpdate && `| ${lastUpdate.toLocaleTimeString()}`}
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
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <StatsCards readings={readings} />

      {/* Category Distribution */}
      <div className="bg-card rounded-lg p-4 border border-border">
        <h3 className="text-sm font-medium text-muted-foreground mb-3">
          AQI Category Distribution
        </h3>
        <AQICategoryBadges readings={readings} />
      </div>

      {/* Map + Station List */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-card rounded-lg border border-border overflow-hidden">
          <div className="p-3 border-b border-border flex items-center justify-between">
            <h3 className="text-sm font-medium">Station Map</h3>
            <span className="text-xs text-muted-foreground">
              {aqiReadings.length} stations
            </span>
          </div>
          <AQIMap
            readings={readings}
            onStationClick={handleStationClick}
            center={[22.5, 80.0]}
            zoom={5}
            className="h-[450px]"
          />
        </div>

        <div className="bg-card rounded-lg border border-border">
          <div className="p-3 border-b border-border">
            <h3 className="text-sm font-medium">Stations (by AQI)</h3>
          </div>
          <StationList
            readings={readings}
            onStationClick={handleStationClick}
          />
        </div>
      </div>

      {/* Selected Station Detail */}
      {selectedStation && (
        <div className="bg-card rounded-lg border border-border p-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-medium">
                Station: {selectedStation}
                {selectedCity && (
                  <span className="text-muted-foreground ml-2">
                    ({selectedCity})
                  </span>
                )}
              </h3>
              <p className="text-xs text-muted-foreground mt-1">
                Individual pollutant concentrations
              </p>
            </div>
            <button
              onClick={() => setSelectedStation(null)}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Close
            </button>
          </div>
          <PollutantChart readings={readings} stationId={selectedStation} />
        </div>
      )}
    </div>
  );
}
