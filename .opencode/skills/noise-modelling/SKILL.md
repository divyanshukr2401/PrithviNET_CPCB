---
name: noise-modelling
description: Generate CNOSSOS-EU compliant environmental noise maps using NoiseModelling library with PostGIS terrain integration
license: MIT
compatibility: opencode
metadata:
  domain: environmental-acoustics
  difficulty: intermediate
  tools: NoiseModelling, PostGIS
---

# Environmental Noise Modelling and Acoustic Heatmaps

## Overview
This skill enables generation of dynamic environmental noise propagation maps using the open-source NoiseModelling library, compliant with CNOSSOS-EU standards. Produces acoustic heatmaps that visualize noise pollution across urban terrain.

## Key Technologies

### NoiseModelling
- Open-source Java/Python library
- CNOSSOS-EU methodology compliant
- Links directly with PostGIS spatial databases
- Supports TIN (Triangulated Irregular Network) terrain models

### CNOSSOS-EU Standard
- Common NOise aSSessment methOdS for Europe
- Standardized calculation method for environmental noise
- Covers road, rail, aircraft, and industrial noise
- Outputs: Lden (day-evening-night), Lnight indicators

## Core Concepts

### Noise Indicators
- **Leq**: Equivalent continuous sound level
- **Lday**: Average level 07:00-19:00
- **Levening**: Average level 19:00-23:00
- **Lnight**: Average level 23:00-07:00
- **Lden**: Day-evening-night weighted indicator

### Sound Propagation Factors
- Source power levels
- Distance attenuation
- Ground absorption
- Atmospheric absorption
- Terrain diffraction
- Building reflections

## Implementation Pattern

### NoiseModelling with Python Bindings
```python
import subprocess
import json
from pathlib import Path

class NoiseModellingWrapper:
    """Wrapper for NoiseModelling Java library"""
    
    def __init__(self, nm_jar_path: str, postgis_config: dict):
        self.nm_jar = Path(nm_jar_path)
        self.db_config = postgis_config
    
    def generate_noise_map(
        self,
        bbox: tuple,  # (minLon, minLat, maxLon, maxLat)
        sources: list,
        receivers_grid_size: int = 50,
        output_format: str = "geojson"
    ) -> dict:
        """
        Generate noise propagation map for given area
        
        Args:
            bbox: Bounding box coordinates
            sources: List of noise source definitions
            receivers_grid_size: Grid spacing in meters
            output_format: Output format (geojson, shapefile)
        """
        # Build NoiseModelling configuration
        config = {
            "database": self.db_config,
            "bbox": {
                "minLon": bbox[0],
                "minLat": bbox[1],
                "maxLon": bbox[2],
                "maxLat": bbox[3]
            },
            "sources": sources,
            "receivers": {
                "type": "grid",
                "delta": receivers_grid_size
            },
            "propagation": {
                "maxSrcDist": 500,
                "maxRefDist": 50,
                "wallAlpha": 0.1,
                "threadCount": 4
            }
        }
        
        # Write config and execute
        config_path = Path("temp_nm_config.json")
        config_path.write_text(json.dumps(config))
        
        result = subprocess.run(
            ["java", "-jar", str(self.nm_jar), str(config_path)],
            capture_output=True,
            text=True
        )
        
        # Parse and return results
        return self._parse_output(result.stdout, output_format)
    
    def _parse_output(self, output: str, format: str) -> dict:
        # Parse NoiseModelling output to GeoJSON
        # Implementation depends on NM version
        pass
```

### PostGIS Terrain Data Setup
```sql
-- Create terrain model table
CREATE TABLE terrain_elevation (
    id SERIAL PRIMARY KEY,
    geom GEOMETRY(POINTZ, 4326),
    elevation FLOAT
);

-- Create buildings table for sound barriers
CREATE TABLE buildings (
    id SERIAL PRIMARY KEY,
    geom GEOMETRY(POLYGONZ, 4326),
    height FLOAT,
    ground_absorption FLOAT DEFAULT 0.5
);

-- Create road network for traffic noise
CREATE TABLE roads (
    id SERIAL PRIMARY KEY,
    geom GEOMETRY(LINESTRING, 4326),
    road_type VARCHAR(50),
    traffic_volume_day INT,
    traffic_volume_night INT,
    speed_limit INT
);

-- Spatial indexes
CREATE INDEX idx_terrain_geom ON terrain_elevation USING GIST(geom);
CREATE INDEX idx_buildings_geom ON buildings USING GIST(geom);
CREATE INDEX idx_roads_geom ON roads USING GIST(geom);
```

### Traffic Noise Source Calculation
```python
def calculate_road_noise_power(
    traffic_volume: int,
    speed_kmh: int,
    heavy_vehicle_percent: float = 0.1
) -> float:
    """
    Calculate road traffic noise source power (Lw) using CNOSSOS
    
    Returns sound power level in dB(A)
    """
    # Light vehicles
    lv_volume = traffic_volume * (1 - heavy_vehicle_percent)
    lv_noise = 79.7 + 10 * np.log10(lv_volume) + 0.95 * np.log10(speed_kmh / 70)
    
    # Heavy vehicles
    hv_volume = traffic_volume * heavy_vehicle_percent
    hv_noise = 84.0 + 10 * np.log10(hv_volume) + 0.75 * np.log10(speed_kmh / 70)
    
    # Combine (logarithmic addition)
    total = 10 * np.log10(10**(lv_noise/10) + 10**(hv_noise/10))
    
    return total
```

### API Endpoint Pattern
```python
@router.get("/noise/heatmap")
async def get_noise_heatmap(
    bbox: str,  # "minLon,minLat,maxLon,maxLat"
    resolution: int = 50,
    time_period: str = "Lden"
):
    """Generate noise heatmap for bounding box"""
    
    coords = [float(x) for x in bbox.split(",")]
    
    # Fetch terrain and sources from PostGIS
    terrain = await fetch_terrain_model(coords)
    buildings = await fetch_buildings(coords)
    roads = await fetch_roads_with_traffic(coords)
    
    # Calculate noise sources from roads
    sources = [
        {
            "geometry": road["geom"],
            "lw_day": calculate_road_noise_power(road["traffic_day"], road["speed"]),
            "lw_night": calculate_road_noise_power(road["traffic_night"], road["speed"])
        }
        for road in roads
    ]
    
    # Generate noise map
    nm = NoiseModellingWrapper(NM_JAR_PATH, POSTGIS_CONFIG)
    result = nm.generate_noise_map(
        bbox=tuple(coords),
        sources=sources,
        receivers_grid_size=resolution
    )
    
    return {
        "type": "FeatureCollection",
        "features": result["features"],
        "metadata": {
            "model": "NoiseModelling",
            "standard": "CNOSSOS-EU",
            "indicator": time_period,
            "resolution_m": resolution
        }
    }
```

### Visualization Color Scale (Lden)
```python
NOISE_COLOR_SCALE = {
    (0, 45): "#00ff00",    # Green - Very quiet
    (45, 50): "#80ff00",   # Light green
    (50, 55): "#ffff00",   # Yellow - Moderate
    (55, 60): "#ffbf00",   # Orange
    (60, 65): "#ff8000",   # Dark orange
    (65, 70): "#ff4000",   # Red-orange
    (70, 75): "#ff0000",   # Red - Loud
    (75, 100): "#800000"   # Dark red - Very loud
}
```

## CPCB Noise Standards (India)
| Zone | Day Limit | Night Limit |
|------|-----------|-------------|
| Industrial | 75 dB(A) | 70 dB(A) |
| Commercial | 65 dB(A) | 55 dB(A) |
| Residential | 55 dB(A) | 45 dB(A) |
| Silence | 50 dB(A) | 40 dB(A) |

## Best Practices
1. Use TIN terrain models for accurate diffraction calculation
2. Include buildings as sound barriers
3. Cache computed noise maps with TTL
4. Use appropriate grid resolution (50m urban, 100m rural)
5. Validate against measured noise levels when possible

## References
- NoiseModelling: https://noise-planet.org/noisemodelling.html
- CNOSSOS-EU: https://ec.europa.eu/environment/noise/
- NoiseModelling GitHub: https://github.com/Universite-Gustave-Eiffel/NoiseModelling
