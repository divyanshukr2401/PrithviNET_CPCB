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

// Water quality gradient — rescaled for actual data distribution
// 86% of stations have WQI 0–0.1, so we spread the blue range to show variation
// Breakpoints: Excellent ≤0.15, Good 0.15–0.3, Fair 0.3–0.5, Poor 0.5–0.7, Very Poor >0.7
const WATER_QUALITY_GRADIENT: Record<number, string> = {
  0.0: "#0571b0",    // Deep blue — excellent (WQI near 0)
  0.15: "#92c5de",   // Light blue — good
  0.3: "#eab308",    // Amber — fair
  0.5: "#f4a582",    // Orange — poor
  0.7: "#ca0020",    // Red — very poor
  1.0: "#7f0000",    // Dark red — extreme
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
        radius={7}
        gradient={WATER_QUALITY_GRADIENT}
      />
    </div>
  );
}
