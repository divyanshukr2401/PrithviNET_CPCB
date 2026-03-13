"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import type { AirReading } from "@/lib/types";
import { getAQIColor, getAQICategory } from "@/lib/types";

// Single dynamic import for the entire map wrapper (avoids 5 separate dynamic() calls)
const LeafletMap = dynamic(() => import("./leaflet-map-wrapper"), {
  ssr: false,
  loading: () => (
    <div className="bg-card rounded-lg flex items-center justify-center h-full">
      <p className="text-muted-foreground">Loading map...</p>
    </div>
  ),
});

interface AQIMapProps {
  readings: AirReading[];
  onStationClick?: (stationId: string) => void;
  center?: [number, number];
  zoom?: number;
  className?: string;
}

export function AQIMap({
  readings,
  onStationClick,
  center = [22.5, 80.0],
  zoom = 5,
  className = "",
}: AQIMapProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div
        className={`bg-card rounded-lg flex items-center justify-center ${className}`}
      >
        <p className="text-muted-foreground">Loading map...</p>
      </div>
    );
  }

  // Filter to only AQI readings with valid coordinates
  const aqiReadings = readings.filter(
    (r) => r.parameter === "AQI" && r.latitude !== 0 && r.longitude !== 0
  );

  return (
    <div className={`rounded-lg overflow-hidden ${className}`}>
      <LeafletMap
        aqiReadings={aqiReadings}
        center={center}
        zoom={zoom}
        onStationClick={onStationClick}
        getAQIColor={getAQIColor}
        getAQICategory={getAQICategory}
      />
    </div>
  );
}
