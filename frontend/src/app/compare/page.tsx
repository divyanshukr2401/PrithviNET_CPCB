"use client";

import { useEffect, useState, useCallback } from "react";
import { getLiveAir, getStations } from "@/lib/api";
import type { AirReading } from "@/lib/types";
import { getAQIColor, getAQICategory, getAQITextOnColor } from "@/lib/types";
import { AQIGauge } from "@/components/charts";
import { RefreshCw, Plus, X } from "lucide-react";

const POLLUTANT_LABELS: Record<string, string> = {
  "PM2.5": "PM2.5 (\u00b5g/m\u00b3)",
  PM10: "PM10 (\u00b5g/m\u00b3)",
  NO2: "NO\u2082 (\u00b5g/m\u00b3)",
  SO2: "SO\u2082 (\u00b5g/m\u00b3)",
  CO: "CO (mg/m\u00b3)",
  O3: "O\u2083 (\u00b5g/m\u00b3)",
  NH3: "NH\u2083 (\u00b5g/m\u00b3)",
  Pb: "Pb (\u00b5g/m\u00b3)",
};

const MAX_PANELS = 4;

interface CityData {
  cityName: string;
  aqiReading: AirReading | null;
  pollutants: AirReading[];
}

export default function ComparePage() {
  const [allReadings, setAllReadings] = useState<AirReading[]>([]);
  const [allCities, setAllCities] = useState<string[]>([]);
  const [cityStateMap, setCityStateMap] = useState<Record<string, string>>({});
  const [selectedCities, setSelectedCities] = useState<(string | null)[]>([null, null]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      getLiveAir({ include_pollutants: true }),
      getStations(),
    ])
      .then(([liveData, stationData]) => {
        setAllReadings(liveData.readings);

        // Build city list and city->state map
        const citiesSet = new Set<string>();
        const csMap: Record<string, string> = {};
        stationData.stations.forEach((s) => {
          if (s.city) {
            citiesSet.add(s.city);
            csMap[s.city] = s.state;
          }
        });
        // Also add cities from live data (in case stations API misses some)
        liveData.readings.forEach((r) => {
          if (r.city && r.parameter === "AQI") citiesSet.add(r.city);
        });
        setAllCities(Array.from(citiesSet).sort());
        setCityStateMap(csMap);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to fetch data");
      })
      .finally(() => setLoading(false));
  }, []);

  // Build city data for a given city name
  const getCityData = useCallback(
    (cityName: string | null): CityData | null => {
      if (!cityName) return null;
      // Get all AQI readings for this city
      const cityAqiReadings = allReadings.filter(
        (r) => r.city === cityName && r.parameter === "AQI"
      );
      if (cityAqiReadings.length === 0) return null;

      // Average AQI across stations
      const avgAqi = Math.round(
        cityAqiReadings.reduce((s, r) => s + r.aqi, 0) / cityAqiReadings.length
      );

      // Use the first station's reading as representative, but override AQI
      const representative = { ...cityAqiReadings[0], aqi: avgAqi };

      // Get pollutant readings from the first station that has them
      const firstStationId = cityAqiReadings[0].station_id;
      const pollutants = allReadings.filter(
        (r) => r.station_id === firstStationId && r.parameter !== "AQI"
      );

      return {
        cityName,
        aqiReading: representative,
        pollutants,
      };
    },
    [allReadings]
  );

  const handleCityChange = (index: number, city: string) => {
    const updated = [...selectedCities];
    updated[index] = city || null;
    setSelectedCities(updated);
  };

  const addPanel = () => {
    if (selectedCities.length < MAX_PANELS) {
      setSelectedCities([...selectedCities, null]);
    }
  };

  const removePanel = (index: number) => {
    if (selectedCities.length > 2) {
      setSelectedCities(selectedCities.filter((_, i) => i !== index));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-primary mx-auto mb-3" />
          <p className="text-muted-foreground">Loading data for comparison...</p>
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Compare Cities</h1>
          <p className="text-muted-foreground text-sm mt-0.5">
            Side-by-side AQI comparison of up to {MAX_PANELS} cities
          </p>
        </div>
        {selectedCities.length < MAX_PANELS && (
          <button
            onClick={addPanel}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-xs text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            Add City
          </button>
        )}
      </div>

      {/* Comparison Panels */}
      <div
        className="grid gap-5"
        style={{
          gridTemplateColumns: `repeat(${selectedCities.length}, minmax(0, 1fr))`,
        }}
      >
        {selectedCities.map((city, index) => {
          const cityData = getCityData(city);
          return (
            <div
              key={index}
              className="bg-card rounded-lg border border-border overflow-hidden flex flex-col"
            >
              {/* City selector header */}
              <div className="p-3 border-b border-border flex items-center gap-2">
                <select
                  value={city || ""}
                  onChange={(e) => handleCityChange(index, e.target.value)}
                  className="flex-1 px-2 py-1.5 rounded border border-border bg-background text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="">Select City...</option>
                  {allCities.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
                {selectedCities.length > 2 && (
                  <button
                    onClick={() => removePanel(index)}
                    className="p-1 rounded text-muted-foreground hover:text-destructive hover:bg-muted/50"
                    title="Remove"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>

              {/* City data */}
              {!city ? (
                <div className="flex-1 flex items-center justify-center p-8">
                  <p className="text-muted-foreground text-sm text-center">
                    Select a city to compare
                  </p>
                </div>
              ) : !cityData ? (
                <div className="flex-1 flex items-center justify-center p-8">
                  <p className="text-muted-foreground text-sm text-center">
                    No data available for {city}
                  </p>
                </div>
              ) : (
                <div className="flex flex-col items-center p-4 gap-3">
                  {/* City name + state */}
                  <div className="text-center">
                    <h3 className="font-semibold text-lg">{city}</h3>
                    {cityStateMap[city] && (
                      <p className="text-xs text-muted-foreground">
                        {cityStateMap[city]}
                      </p>
                    )}
                  </div>

                  {/* AQI Gauge */}
                  <div className="relative">
                    <AQIGauge aqi={cityData.aqiReading!.aqi} size={130} />
                  </div>

                  {/* Pollutant table */}
                  {cityData.pollutants.length > 0 && (
                    <div className="w-full mt-2">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="text-muted-foreground border-b border-border/50">
                            <th className="text-left py-1.5 px-1">Pollutant</th>
                            <th className="text-right py-1.5 px-1">Value</th>
                          </tr>
                        </thead>
                        <tbody>
                          {cityData.pollutants.map((p) => {
                            const color = getAQIColor(p.aqi || 0);
                            return (
                              <tr
                                key={p.parameter}
                                className="border-b border-border/20"
                              >
                                <td className="py-1.5 px-1 font-medium">
                                  {POLLUTANT_LABELS[p.parameter] || p.parameter}
                                </td>
                                <td className="py-1.5 px-1 text-right font-mono">
                                  {p.value.toFixed(1)}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* Timestamp */}
                  {cityData.aqiReading && (
                    <p className="text-[10px] text-muted-foreground mt-1">
                      {new Date(cityData.aqiReading.timestamp).toLocaleString()}
                    </p>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
