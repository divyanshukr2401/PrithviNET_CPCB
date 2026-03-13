"use client";

import { useEffect, useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { getStations } from "@/lib/api";
import { MapPin, Search, Filter, RefreshCw, ArrowRight } from "lucide-react";

// ── Types ─────────────────────────────────────────────────
interface StationItem {
  station_id: string;
  station_name: string;
  city: string;
  state: string;
  latitude: number;
  longitude: number;
}

// ── Page Component ────────────────────────────────────────
export default function StationsPage() {
  const router = useRouter();
  const [stations, setStations] = useState<StationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedState, setSelectedState] = useState<string>("");

  // ── Load stations on mount ──────────────────────────────
  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await getStations();
        if (!cancelled) {
          setStations(data.stations);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to load stations"
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  // ── Derived data ────────────────────────────────────────
  const uniqueStates = useMemo(() => {
    const states = Array.from(new Set(stations.map((s) => s.state)));
    return states.sort((a, b) => a.localeCompare(b));
  }, [stations]);

  const filteredStations = useMemo(() => {
    let result = stations;

    // State filter
    if (selectedState) {
      result = result.filter((s) => s.state === selectedState);
    }

    // Text search filter
    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase();
      result = result.filter(
        (s) =>
          s.station_name.toLowerCase().includes(q) ||
          s.city.toLowerCase().includes(q) ||
          s.state.toLowerCase().includes(q)
      );
    }

    return result;
  }, [stations, searchQuery, selectedState]);

  // ── Render ──────────────────────────────────────────────
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <MapPin className="w-6 h-6 text-primary" />
          Monitoring Stations
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Browse all CPCB air quality monitoring stations across India.
          {!loading && !error && (
            <span className="ml-1">
              Showing{" "}
              <span className="text-foreground font-medium">
                {filteredStations.length}
              </span>{" "}
              of{" "}
              <span className="text-foreground font-medium">
                {stations.length}
              </span>{" "}
              stations.
            </span>
          )}
        </p>
      </div>

      {/* ═══════════════════════════════════════════════════
          Filters
          ═══════════════════════════════════════════════════ */}
      <div className="bg-card rounded-lg border border-border p-5">
        <h2 className="text-sm font-medium text-muted-foreground mb-4 flex items-center gap-2">
          <Filter className="w-4 h-4" />
          Filters
        </h2>
        <div className="flex flex-col sm:flex-row gap-4">
          {/* Text Search */}
          <div className="flex-1">
            <label
              htmlFor="station-search"
              className="block text-xs font-medium text-muted-foreground mb-1.5"
            >
              Search
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/50" />
              <input
                id="station-search"
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by station name, city, or state..."
                className="w-full rounded-lg border border-border bg-card text-foreground pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 placeholder:text-muted-foreground/50"
              />
            </div>
          </div>

          {/* State Filter */}
          <div className="sm:w-64">
            <label
              htmlFor="state-filter"
              className="block text-xs font-medium text-muted-foreground mb-1.5"
            >
              State
            </label>
            <select
              id="state-filter"
              value={selectedState}
              onChange={(e) => setSelectedState(e.target.value)}
              className="w-full rounded-lg border border-border bg-card text-foreground px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
            >
              <option value="">All States</option>
              {uniqueStates.map((state) => (
                <option key={state} value={state}>
                  {state}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════
          Loading State
          ═══════════════════════════════════════════════════ */}
      {loading && (
        <div className="bg-card rounded-lg border border-border p-12 text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-primary mx-auto mb-3" />
          <p className="text-muted-foreground text-sm">
            Loading monitoring stations...
          </p>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════
          Error State
          ═══════════════════════════════════════════════════ */}
      {error && (
        <div className="bg-card rounded-lg border border-red-500/30 p-5">
          <p className="text-red-400 font-medium text-sm">
            Failed to load stations
          </p>
          <p className="text-muted-foreground text-sm mt-1">{error}</p>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════
          Empty State
          ═══════════════════════════════════════════════════ */}
      {!loading && !error && stations.length === 0 && (
        <div className="bg-card rounded-lg border border-border p-12 text-center">
          <MapPin className="w-10 h-10 text-muted-foreground/40 mx-auto mb-3" />
          <p className="text-muted-foreground text-sm">
            No monitoring stations found.
          </p>
        </div>
      )}

      {/* No results from filter */}
      {!loading &&
        !error &&
        stations.length > 0 &&
        filteredStations.length === 0 && (
          <div className="bg-card rounded-lg border border-border p-12 text-center">
            <Search className="w-10 h-10 text-muted-foreground/40 mx-auto mb-3" />
            <p className="text-muted-foreground text-sm">
              No stations match your search criteria. Try adjusting the filters.
            </p>
          </div>
        )}

      {/* ═══════════════════════════════════════════════════
          Stations Table
          ═══════════════════════════════════════════════════ */}
      {!loading && !error && filteredStations.length > 0 && (
        <div className="bg-card rounded-lg border border-border overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/20">
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                    Station ID
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                    Station Name
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                    City
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                    State
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground">
                    Latitude
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground">
                    Longitude
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-muted-foreground">
                    Forecast
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredStations.map((station) => (
                  <tr
                    key={station.station_id}
                    onClick={() => router.push(`/forecast?station=${station.station_id}`)}
                    className="border-b border-border/50 hover:bg-muted/20 transition-colors cursor-pointer group"
                  >
                    <td className="px-4 py-3">
                      <span className="font-mono text-xs text-primary">
                        {station.station_id}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <MapPin className="w-3.5 h-3.5 text-muted-foreground/50 flex-shrink-0" />
                        <span className="font-medium text-foreground">
                          {station.station_name}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {station.city}
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex px-2 py-0.5 rounded-full bg-primary/10 text-primary text-xs font-medium border border-primary/20">
                        {station.state}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-xs text-muted-foreground">
                      {station.latitude.toFixed(4)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-xs text-muted-foreground">
                      {station.longitude.toFixed(4)}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <ArrowRight className="w-4 h-4 text-muted-foreground/30 group-hover:text-primary transition-colors mx-auto" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Footer count */}
          <div className="px-4 py-3 border-t border-border bg-muted/10 flex items-center justify-between text-xs text-muted-foreground">
            <span>
              {filteredStations.length} station
              {filteredStations.length !== 1 ? "s" : ""} displayed
            </span>
            {(searchQuery || selectedState) && (
              <button
                onClick={() => {
                  setSearchQuery("");
                  setSelectedState("");
                }}
                className="text-primary hover:text-primary/80 transition-colors font-medium"
              >
                Clear filters
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
