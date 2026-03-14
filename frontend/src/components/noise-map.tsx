"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import type { NoiseStation } from "@/lib/types";

const NoiseLeafletMap = dynamic(() => import("./noise-map-wrapper"), {
  ssr: false,
  loading: () => (
    <div className="bg-card rounded-lg flex items-center justify-center h-full">
      <p className="text-muted-foreground">Loading noise map...</p>
    </div>
  ),
});

interface NoiseMapProps {
  stations: NoiseStation[];
  onStationClick?: (stationId: string) => void;
  selectedStationId?: string | null;
  center?: [number, number];
  zoom?: number;
  className?: string;
}

export function NoiseMap({
  stations,
  onStationClick,
  selectedStationId,
  center = [22.5, 80.0],
  zoom = 5,
  className = "",
}: NoiseMapProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div
        className={`bg-card rounded-lg flex items-center justify-center ${className}`}
      >
        <p className="text-muted-foreground">Loading noise map...</p>
      </div>
    );
  }

  return (
    <div className={`rounded-lg overflow-hidden ${className}`}>
      <NoiseLeafletMap
        stations={stations}
        onStationClick={onStationClick}
        selectedStationId={selectedStationId}
        center={center}
        zoom={zoom}
      />
    </div>
  );
}
