"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import type { DistrictNoiseData } from "@/lib/types";

const DistrictNoiseLeafletMap = dynamic(
  () => import("./district-noise-map-wrapper"),
  {
    ssr: false,
    loading: () => (
      <div className="bg-card rounded-lg flex items-center justify-center h-full">
        <p className="text-muted-foreground">Loading district noise map...</p>
      </div>
    ),
  }
);

interface DistrictNoiseMapProps {
  districts: DistrictNoiseData[];
  onDistrictClick?: (districtId: string) => void;
  selectedDistrictId?: string | null;
  center?: [number, number];
  zoom?: number;
  className?: string;
}

export function DistrictNoiseMap({
  districts,
  onDistrictClick,
  selectedDistrictId,
  center = [22.5, 80.0],
  zoom = 5,
  className = "",
}: DistrictNoiseMapProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div
        className={`bg-card rounded-lg flex items-center justify-center ${className}`}
      >
        <p className="text-muted-foreground">Loading district noise map...</p>
      </div>
    );
  }

  return (
    <div className={`rounded-lg overflow-hidden ${className}`}>
      <DistrictNoiseLeafletMap
        districts={districts}
        onDistrictClick={onDistrictClick}
        selectedDistrictId={selectedDistrictId}
        center={center}
        zoom={zoom}
      />
    </div>
  );
}
