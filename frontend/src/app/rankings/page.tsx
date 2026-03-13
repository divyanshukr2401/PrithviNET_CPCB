"use client";

import { useEffect, useState, useMemo } from "react";
import { getLiveAir, getStations } from "@/lib/api";
import type { AirReading } from "@/lib/types";
import {
  getAQIColor,
  getAQICategory,
  getAQITextOnColor,
  CPCB_AQI_COLORS,
  AQI_CATEGORIES_ORDERED,
} from "@/lib/types";
import { RefreshCw, Search, ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";

interface CityRanking {
  rank: number;
  city: string;
  state: string;
  avgAqi: number;
  stationCount: number;
  category: string;
}

type SortField = "rank" | "city" | "state" | "avgAqi";
type SortDir = "asc" | "desc";

export default function RankingsPage() {
  const [readings, setReadings] = useState<AirReading[]>([]);
  const [stationStateMap, setStationStateMap] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortField, setSortField] = useState<SortField>("rank");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  useEffect(() => {
    Promise.all([
      getLiveAir({ include_pollutants: false }),
      getStations(),
    ])
      .then(([liveData, stationData]) => {
        setReadings(liveData.readings);
        const stateMap: Record<string, string> = {};
        stationData.stations.forEach((s) => {
          stateMap[s.station_id] = s.state;
        });
        setStationStateMap(stateMap);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to fetch data");
      })
      .finally(() => setLoading(false));
  }, []);

  // Aggregate by city
  const rankings: CityRanking[] = useMemo(() => {
    const aqiReadings = readings.filter((r) => r.parameter === "AQI");
    const cityMap: Record<string, { totalAqi: number; count: number; state: string }> = {};

    aqiReadings.forEach((r) => {
      const key = r.city;
      if (!cityMap[key]) {
        cityMap[key] = {
          totalAqi: 0,
          count: 0,
          state: stationStateMap[r.station_id] || "—",
        };
      }
      cityMap[key].totalAqi += r.aqi;
      cityMap[key].count += 1;
    });

    const sorted = Object.entries(cityMap)
      .map(([city, data]) => ({
        city,
        state: data.state,
        avgAqi: Math.round(data.totalAqi / data.count),
        stationCount: data.count,
        category: getAQICategory(Math.round(data.totalAqi / data.count)),
      }))
      .sort((a, b) => a.avgAqi - b.avgAqi) // Best first by default
      .map((item, idx) => ({ ...item, rank: idx + 1 }));

    return sorted;
  }, [readings, stationStateMap]);

  // Filter + sort
  const displayRankings = useMemo(() => {
    let filtered = rankings;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      filtered = rankings.filter(
        (r) =>
          r.city.toLowerCase().includes(q) ||
          r.state.toLowerCase().includes(q)
      );
    }

    const sorted = [...filtered].sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case "rank":
          cmp = a.rank - b.rank;
          break;
        case "city":
          cmp = a.city.localeCompare(b.city);
          break;
        case "state":
          cmp = a.state.localeCompare(b.state);
          break;
        case "avgAqi":
          cmp = a.avgAqi - b.avgAqi;
          break;
      }
      return sortDir === "desc" ? -cmp : cmp;
    });

    return sorted;
  }, [rankings, searchQuery, sortField, sortDir]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDir("asc");
    }
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return <ArrowUpDown className="w-3 h-3 opacity-30" />;
    return sortDir === "asc" ? (
      <ArrowUp className="w-3 h-3" />
    ) : (
      <ArrowDown className="w-3 h-3" />
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-primary mx-auto mb-3" />
          <p className="text-muted-foreground">Loading city rankings...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center bg-card p-8 rounded-lg border border-border max-w-md">
          <p className="text-destructive font-medium mb-2">Error</p>
          <p className="text-muted-foreground text-sm">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">City Rankings</h1>
        <p className="text-muted-foreground text-sm mt-0.5">
          Cities ranked by average AQI across all monitoring stations
        </p>
      </div>

      {/* Search + Summary */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-[200px] max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search city or state..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded-lg border border-border bg-card text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>
        <span className="text-xs text-muted-foreground">
          {displayRankings.length} of {rankings.length} cities
        </span>
      </div>

      {/* Category summary bar */}
      <div className="flex flex-wrap gap-2">
        {AQI_CATEGORIES_ORDERED.map((cat) => {
          const count = rankings.filter((r) => r.category === cat).length;
          if (count === 0) return null;
          return (
            <span
              key={cat}
              className="px-2.5 py-1 rounded-full text-xs font-medium"
              style={{
                backgroundColor: CPCB_AQI_COLORS[cat] + "22",
                color: CPCB_AQI_COLORS[cat],
              }}
            >
              {cat}: {count}
            </span>
          );
        })}
      </div>

      {/* Rankings Table */}
      <div className="bg-card rounded-lg border border-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/30">
              <tr className="text-xs uppercase text-muted-foreground">
                <th
                  className="text-center py-3 px-3 cursor-pointer hover:text-foreground"
                  onClick={() => handleSort("rank")}
                >
                  <span className="inline-flex items-center gap-1">
                    Rank <SortIcon field="rank" />
                  </span>
                </th>
                <th
                  className="text-left py-3 px-3 cursor-pointer hover:text-foreground"
                  onClick={() => handleSort("city")}
                >
                  <span className="inline-flex items-center gap-1">
                    City <SortIcon field="city" />
                  </span>
                </th>
                <th
                  className="text-left py-3 px-3 cursor-pointer hover:text-foreground"
                  onClick={() => handleSort("state")}
                >
                  <span className="inline-flex items-center gap-1">
                    State <SortIcon field="state" />
                  </span>
                </th>
                <th className="text-center py-3 px-3">Stations</th>
                <th className="text-center py-3 px-3">Remark</th>
                <th
                  className="text-center py-3 px-3 cursor-pointer hover:text-foreground"
                  onClick={() => handleSort("avgAqi")}
                >
                  <span className="inline-flex items-center gap-1">
                    AQI <SortIcon field="avgAqi" />
                  </span>
                </th>
              </tr>
            </thead>
            <tbody>
              {displayRankings.map((r) => {
                const color = getAQIColor(r.avgAqi);
                const textOnColor = getAQITextOnColor(r.avgAqi);
                return (
                  <tr
                    key={r.city}
                    className="border-t border-border/30 hover:bg-muted/20 transition-colors"
                  >
                    <td className="text-center py-2.5 px-3 font-mono text-xs">
                      {r.rank}
                    </td>
                    <td className="py-2.5 px-3 font-medium">{r.city}</td>
                    <td className="py-2.5 px-3 text-muted-foreground text-xs">
                      {r.state}
                    </td>
                    <td className="text-center py-2.5 px-3 text-xs text-muted-foreground">
                      {r.stationCount}
                    </td>
                    <td className="text-center py-2.5 px-3">
                      <span
                        className="px-2 py-0.5 rounded text-[10px] font-semibold"
                        style={{ backgroundColor: color, color: textOnColor }}
                      >
                        {r.category}
                      </span>
                    </td>
                    <td className="text-center py-2.5 px-3">
                      <span className="font-bold" style={{ color }}>
                        {r.avgAqi}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
