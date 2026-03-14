"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import type { HeatmapPoint } from "./heatmap-wrapper";

// Dynamic import with SSR disabled (Leaflet needs window/document)
const HeatmapWrapper = dynamic(() => import("./heatmap-wrapper"), {
  ssr: false,
  loading: () => (
    <div className="bg-card rounded-lg flex items-center justify-center h-full">
      <p className="text-muted-foreground">Loading water quality map...</p>
    </div>
  ),
});

// Water quality heatmap gradient: blue (clean) → yellow → red (polluted)
const WATER_QUALITY_GRADIENT: Record<number, string> = {
  0.0: "#0571b0",   // Deep blue - excellent
  0.25: "#92c5de",  // Light blue - good
  0.5: "#f7f056",   // Yellow - fair
  0.75: "#f4a582",  // Orange - poor
  1.0: "#ca0020",   // Red - very poor
};

interface WaterQualityMapProps {
  points: HeatmapPoint[];
  center?: [number, number];
  zoom?: number;
  className?: string;
}

export function WaterQualityMap({
  points,
  center = [22.5, 80.0],
  zoom = 5,
  className = "",
}: WaterQualityMapProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div
        className={`bg-card rounded-lg flex items-center justify-center ${className}`}
      >
        <p className="text-muted-foreground">Loading water quality map...</p>
      </div>
    );
  }

  return (
    <div className={`rounded-lg overflow-hidden ${className}`}>
      <HeatmapWrapper
        points={points}
        center={center}
        zoom={zoom}
        radius={28}
        blur={18}
        max={1.0}
        gradient={WATER_QUALITY_GRADIENT}
      />
    </div>
  );
}
