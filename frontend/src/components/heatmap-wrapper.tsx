"use client";

import { useEffect, useRef } from "react";
import {
  MapContainer,
  TileLayer,
  useMap,
} from "react-leaflet";
import L from "leaflet";

export interface HeatmapPoint {
  lat: number;
  lng: number;
  intensity: number;
  station_name?: string;
  state?: string;
  district?: string;
  parameters?: Record<string, number>;
}

/**
 * Linearly interpolate between two hex colors.
 * t in [0,1]: 0 = colorA, 1 = colorB.
 */
function lerpColor(a: string, b: string, t: number): string {
  const parse = (hex: string) => {
    const h = hex.replace("#", "");
    return [
      parseInt(h.substring(0, 2), 16),
      parseInt(h.substring(2, 4), 16),
      parseInt(h.substring(4, 6), 16),
    ];
  };
  const [r1, g1, b1] = parse(a);
  const [r2, g2, b2] = parse(b);
  const clamp = (v: number) => Math.max(0, Math.min(255, Math.round(v)));
  const r = clamp(r1 + (r2 - r1) * t);
  const g = clamp(g1 + (g2 - g1) * t);
  const bl = clamp(b1 + (b2 - b1) * t);
  return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${bl.toString(16).padStart(2, "0")}`;
}

/**
 * Map an intensity value (0–1) to a hex color using a gradient with arbitrary stops.
 * Stops: { 0.0: "#aaa", 0.5: "#bbb", 1.0: "#ccc" }
 */
function intensityToColor(
  intensity: number,
  gradient: Record<number, string>
): string {
  const stops = Object.keys(gradient)
    .map(Number)
    .sort((a, b) => a - b);

  if (stops.length === 0) return "#808080";
  if (intensity <= stops[0]) return gradient[stops[0]];
  if (intensity >= stops[stops.length - 1])
    return gradient[stops[stops.length - 1]];

  for (let i = 0; i < stops.length - 1; i++) {
    if (intensity >= stops[i] && intensity <= stops[i + 1]) {
      const t = (intensity - stops[i]) / (stops[i + 1] - stops[i]);
      return lerpColor(gradient[stops[i]], gradient[stops[i + 1]], t);
    }
  }
  return gradient[stops[stops.length - 1]];
}

/**
 * Build an HTML tooltip string for a station point.
 */
/**
 * Get the WQI category label for a given intensity value.
 */
function getWQICategory(intensity: number): string {
  if (intensity <= 0.15) return "Excellent";
  if (intensity <= 0.3) return "Good";
  if (intensity <= 0.5) return "Fair";
  if (intensity <= 0.7) return "Poor";
  return "Very Poor";
}

/**
 * Get the WQI badge color for a given intensity value.
 */
function getWQIBadgeColor(intensity: number): string {
  if (intensity <= 0.15) return "#0571b0";
  if (intensity <= 0.3) return "#92c5de";
  if (intensity <= 0.5) return "#eab308";
  if (intensity <= 0.7) return "#f4a582";
  return "#ca0020";
}

/**
 * Build an HTML tooltip string for a station point (hover).
 */
function buildTooltip(p: HeatmapPoint): string {
  const wqiRaw = p.intensity.toFixed(3);
  const label = getWQICategory(p.intensity);
  const badgeColor = getWQIBadgeColor(p.intensity);

  let html = `<div style="font-family:system-ui,sans-serif;font-size:12px;min-width:180px">`;
  html += `<div style="font-weight:700;font-size:13px;margin-bottom:4px">${p.station_name || "Unknown Station"}</div>`;
  if (p.state) {
    html += `<div style="color:#666;margin-bottom:2px">${p.state}</div>`;
  }
  if (p.district) {
    html += `<div style="color:#888;font-size:11px;margin-bottom:6px">${p.district}</div>`;
  }
  html += `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">`;
  html += `<span style="font-weight:600">WQI: ${wqiRaw} (${label})</span>`;
  html += `<span style="background:${badgeColor};color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600">${label}</span>`;
  html += `</div>`;

  // Show top parameters (up to 6)
  if (p.parameters && Object.keys(p.parameters).length > 0) {
    html += `<div style="border-top:1px solid #e5e7eb;padding-top:4px;margin-top:2px">`;
    const entries = Object.entries(p.parameters).slice(0, 6);
    for (const [name, val] of entries) {
      html += `<div style="display:flex;justify-content:space-between;padding:1px 0;font-size:11px">`;
      html += `<span style="color:#666">${name}</span>`;
      html += `<span style="font-weight:500">${val}</span>`;
      html += `</div>`;
    }
    html += `</div>`;
  }

  html += `</div>`;
  return html;
}

/**
 * Build an HTML popup string for a station point (click — persistent).
 */
function buildPopup(p: HeatmapPoint): string {
  const wqiRaw = p.intensity.toFixed(3);
  const label = getWQICategory(p.intensity);
  const badgeColor = getWQIBadgeColor(p.intensity);

  let html = `<div style="font-family:system-ui,sans-serif;font-size:13px;min-width:220px;max-width:300px">`;
  html += `<div style="font-weight:700;font-size:14px;margin-bottom:4px">${p.station_name || "Unknown Station"}</div>`;
  if (p.state) {
    html += `<div style="color:#555;margin-bottom:2px">${p.state}</div>`;
  }
  if (p.district) {
    html += `<div style="color:#777;font-size:12px;margin-bottom:6px">${p.district}</div>`;
  }
  html += `<div style="display:inline-block;background:${badgeColor};color:#fff;padding:3px 10px;border-radius:12px;font-size:12px;font-weight:600;margin-bottom:8px">`;
  html += `WQI: ${wqiRaw} — ${label}`;
  html += `</div>`;

  // Show ALL parameters
  if (p.parameters && Object.keys(p.parameters).length > 0) {
    html += `<div style="border-top:1px solid #e5e7eb;padding-top:6px;margin-top:4px">`;
    html += `<div style="font-weight:600;font-size:11px;color:#555;margin-bottom:4px">Water Quality Parameters</div>`;
    const entries = Object.entries(p.parameters);
    for (const [name, val] of entries) {
      html += `<div style="display:flex;justify-content:space-between;padding:2px 0;font-size:12px">`;
      html += `<span style="color:#555">${name}</span>`;
      html += `<span style="font-weight:500">${val}</span>`;
      html += `</div>`;
    }
    html += `</div>`;
  }

  html += `</div>`;
  return html;
}

// ── Default gradient (blue → red) ─────────────────────────────
const DEFAULT_GRADIENT: Record<number, string> = {
  0.0: "#0571b0",
  0.25: "#92c5de",
  0.5: "#f7f056",
  0.75: "#f4a582",
  1.0: "#ca0020",
};

interface CircleMarkerLayerProps {
  points: HeatmapPoint[];
  circleRadius?: number;
  gradient?: Record<number, string>;
}

/**
 * Inner component: uses useMap() to create L.circleMarker for each point.
 * Markers are fixed pixel-size — no distortion on zoom.
 */
function CircleMarkerLayer({
  points,
  circleRadius = 6,
  gradient = DEFAULT_GRADIENT,
}: CircleMarkerLayerProps) {
  const map = useMap();
  const layerGroupRef = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    if (!map) return;

    // Remove previous layer group
    if (layerGroupRef.current) {
      map.removeLayer(layerGroupRef.current);
      layerGroupRef.current = null;
    }

    const group = L.layerGroup();

    for (const p of points) {
      const color = intensityToColor(p.intensity, gradient);

      const marker = L.circleMarker([p.lat, p.lng], {
        radius: circleRadius,
        fillColor: color,
        color: "#fff",
        weight: 1.5,
        fillOpacity: 0.85,
        opacity: 0.9,
      });

      // Tooltip on hover
      marker.bindTooltip(buildTooltip(p), {
        direction: "top",
        offset: [0, -8],
        className: "wqi-tooltip",
        sticky: false,
      });

      // Popup on click (persistent, shows full details)
      marker.bindPopup(buildPopup(p), {
        maxWidth: 320,
        className: "wqi-popup",
      });

      // Hover highlight
      marker.on("mouseover", () => {
        marker.setStyle({
          weight: 2.5,
          color: "#1e293b",
          fillOpacity: 1.0,
          radius: circleRadius + 2,
        });
        marker.bringToFront();
      });
      marker.on("mouseout", () => {
        marker.setStyle({
          weight: 1.5,
          color: "#fff",
          fillOpacity: 0.85,
          radius: circleRadius,
        });
      });

      group.addLayer(marker);
    }

    group.addTo(map);
    layerGroupRef.current = group;

    return () => {
      if (layerGroupRef.current) {
        map.removeLayer(layerGroupRef.current);
        layerGroupRef.current = null;
      }
    };
  }, [map, points, circleRadius, gradient]);

  return null;
}

interface HeatmapWrapperProps {
  points: HeatmapPoint[];
  center?: [number, number];
  zoom?: number;
  className?: string;
  radius?: number;
  gradient?: Record<number, string>;
}

export default function HeatmapWrapper({
  points,
  center = [22.5, 80.0],
  zoom = 5,
  className = "",
  radius = 6,
  gradient,
}: HeatmapWrapperProps) {
  return (
    <MapContainer
      center={center}
      zoom={zoom}
      className={`w-full h-full ${className}`}
      style={{ minHeight: "400px" }}
      zoomControl={true}
      scrollWheelZoom={true}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <CircleMarkerLayer
        points={points}
        circleRadius={radius}
        gradient={gradient}
      />
    </MapContainer>
  );
}
