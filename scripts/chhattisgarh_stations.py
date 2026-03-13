"""
Chhattisgarh Environmental Monitoring Station Definitions
=========================================================
41 stations across 6 cities + 20 industrial factories for OCEMS monitoring.
All coordinates are real locations in Chhattisgarh.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class StationType(str, Enum):
    AIR = "air"
    WATER = "water"
    NOISE = "noise"


class ZoneType(str, Enum):
    INDUSTRIAL = "industrial"
    COMMERCIAL = "commercial"
    RESIDENTIAL = "residential"
    SILENCE = "silence"          # near hospitals/schools
    RIVERFRONT = "riverfront"
    MINING = "mining"


@dataclass
class Station:
    station_id: str
    name: str
    city: str
    station_type: StationType
    latitude: float
    longitude: float
    zone: ZoneType
    description: str = ""
    river_name: Optional[str] = None          # water stations only
    factory_proximity_km: Optional[float] = None  # distance to nearest factory


@dataclass
class Factory:
    factory_id: str
    name: str
    city: str
    latitude: float
    longitude: float
    industry_type: str
    emission_params: list[str] = field(default_factory=list)
    description: str = ""


# ---------------------------------------------------------------------------
# AIR QUALITY STATIONS (23 total)
# Parameters: PM2.5, PM10, NO2, SO2, CO, O3, NH3, Pb
# ---------------------------------------------------------------------------

AIR_STATIONS: list[Station] = [
    # --- Raipur (3 stations) ---
    Station("AQ-CG-001", "Raipur Collectorate CAAQMS", "Raipur",
            StationType.AIR, 21.2514, 81.6296, ZoneType.COMMERCIAL,
            "Central Raipur near Collectorate, high-traffic commercial zone"),
    Station("AQ-CG-002", "Mana Camp Industrial CAAQMS", "Raipur",
            StationType.AIR, 21.2200, 81.5700, ZoneType.INDUSTRIAL,
            "Near Urla-Siltara industrial belt, heavy manufacturing area"),
    Station("AQ-CG-003", "Shankar Nagar Residential CAAQMS", "Raipur",
            StationType.AIR, 21.2365, 81.6148, ZoneType.RESIDENTIAL,
            "Dense residential area near Shankar Nagar main road"),

    # --- Bhilai (3 stations) ---
    Station("AQ-CG-004", "BSP Main Gate CAAQMS", "Bhilai",
            StationType.AIR, 21.2094, 81.3784, ZoneType.INDUSTRIAL,
            "Adjacent to Bhilai Steel Plant main entrance, heavy SO2/PM exposure"),
    Station("AQ-CG-005", "Civic Centre CAAQMS", "Bhilai",
            StationType.AIR, 21.2167, 81.4278, ZoneType.COMMERCIAL,
            "Bhilai commercial hub near Civic Centre market area"),
    Station("AQ-CG-006", "Nehru Nagar Residential CAAQMS", "Bhilai",
            StationType.AIR, 21.1983, 81.4100, ZoneType.RESIDENTIAL,
            "BSP township residential area, downwind from steel plant"),

    # --- Korba (3 stations) ---
    Station("AQ-CG-007", "NTPC Korba CAAQMS", "Korba",
            StationType.AIR, 22.3595, 82.7501, ZoneType.INDUSTRIAL,
            "Near NTPC Super Thermal Power Station, coal ash and SO2 hotspot"),
    Station("AQ-CG-008", "Korba City Centre CAAQMS", "Korba",
            StationType.AIR, 22.3490, 82.6830, ZoneType.COMMERCIAL,
            "Korba town commercial area near bus stand"),
    Station("AQ-CG-009", "SECL Gevra Mine CAAQMS", "Korba",
            StationType.AIR, 22.2986, 82.5800, ZoneType.MINING,
            "Near Asia's largest open-cast coal mine, extreme PM10 levels"),

    # --- Bilaspur (2 stations) ---
    Station("AQ-CG-010", "Bilaspur Railway CAAQMS", "Bilaspur",
            StationType.AIR, 22.0796, 82.1391, ZoneType.COMMERCIAL,
            "Near railway junction, diesel particulate + commercial traffic"),
    Station("AQ-CG-011", "Uslapur Industrial CAAQMS", "Bilaspur",
            StationType.AIR, 22.0550, 82.1700, ZoneType.INDUSTRIAL,
            "Uslapur industrial area, cement and rice mills"),

    # --- Durg (2 stations) ---
    Station("AQ-CG-012", "Durg City CAAQMS", "Durg",
            StationType.AIR, 21.1904, 81.2849, ZoneType.COMMERCIAL,
            "Central Durg near clock tower, heavy vehicular traffic"),
    Station("AQ-CG-013", "Durg Industrial Estate CAAQMS", "Durg",
            StationType.AIR, 21.1700, 81.3100, ZoneType.INDUSTRIAL,
            "Near sponge iron and steel rolling mills"),

    # --- Raigarh (2 stations) ---
    Station("AQ-CG-014", "Raigarh City CAAQMS", "Raigarh",
            StationType.AIR, 21.8974, 83.3950, ZoneType.COMMERCIAL,
            "Central Raigarh, commercial + residential mix"),
    Station("AQ-CG-015", "Tamnar Coal Belt CAAQMS", "Raigarh",
            StationType.AIR, 21.7900, 83.3600, ZoneType.MINING,
            "Near Tamnar power plants and coal washeries"),

    # --- Additional high-priority stations ---
    Station("AQ-CG-016", "Siltara GIDC CAAQMS", "Raipur",
            StationType.AIR, 21.3100, 81.5400, ZoneType.INDUSTRIAL,
            "Siltara Growth Centre, largest industrial estate in CG"),
    Station("AQ-CG-017", "Urla Industrial CAAQMS", "Raipur",
            StationType.AIR, 21.2650, 81.5150, ZoneType.INDUSTRIAL,
            "Urla industrial area, diverse manufacturing"),
    Station("AQ-CG-018", "Jamul Cement CAAQMS", "Bhilai",
            StationType.AIR, 21.2500, 81.3200, ZoneType.INDUSTRIAL,
            "Near ACC Jamul Cement Works, high PM and calcium carbonate dust"),
    Station("AQ-CG-019", "BALCO Korba CAAQMS", "Korba",
            StationType.AIR, 22.3200, 82.6900, ZoneType.INDUSTRIAL,
            "Near Bharat Aluminium Company smelter, fluoride emissions"),
    Station("AQ-CG-020", "Kusmunda Mine CAAQMS", "Korba",
            StationType.AIR, 22.3100, 82.6200, ZoneType.MINING,
            "Near Kusmunda open-cast coal mine, heavy PM10"),
    Station("AQ-CG-021", "Bilaspur Torwa CAAQMS", "Bilaspur",
            StationType.AIR, 22.1000, 82.1200, ZoneType.RESIDENTIAL,
            "Torwa residential area, influenced by nearby cement kilns"),
    Station("AQ-CG-022", "Durg Pulgaon CAAQMS", "Durg",
            StationType.AIR, 21.2000, 81.2600, ZoneType.RESIDENTIAL,
            "Pulgaon Chowk residential area, traffic + industrial mix"),
    Station("AQ-CG-023", "Raigarh Lara STPS CAAQMS", "Raigarh",
            StationType.AIR, 21.8100, 83.4200, ZoneType.INDUSTRIAL,
            "Near NTPC Lara Super Thermal Power Station"),
]


# ---------------------------------------------------------------------------
# WATER QUALITY STATIONS (9 total)
# Parameters: pH, DO, BOD, COD, TSS, Turbidity, Conductivity, Temperature,
#             Nitrates, Phosphates
# ---------------------------------------------------------------------------

WATER_STATIONS: list[Station] = [
    # --- Raipur (2 stations) ---
    Station("WQ-CG-001", "Kharun River - Raipur Upstream", "Raipur",
            StationType.WATER, 21.2800, 81.6100, ZoneType.RIVERFRONT,
            "Kharun river upstream of Raipur city, reference/clean station",
            river_name="Kharun"),
    Station("WQ-CG-002", "Kharun River - Raipur Downstream", "Raipur",
            StationType.WATER, 21.2100, 81.6500, ZoneType.RIVERFRONT,
            "Kharun river downstream, receives city sewage discharge",
            river_name="Kharun"),

    # --- Bhilai (1 station) ---
    Station("WQ-CG-003", "Sheonath River - Bhilai", "Bhilai",
            StationType.WATER, 21.2300, 81.3500, ZoneType.INDUSTRIAL,
            "Sheonath river near BSP industrial effluent discharge point",
            river_name="Sheonath", factory_proximity_km=1.2),

    # --- Korba (2 stations) ---
    Station("WQ-CG-004", "Hasdeo River - Korba Upstream", "Korba",
            StationType.WATER, 22.3900, 82.7700, ZoneType.RIVERFRONT,
            "Hasdeo river upstream of NTPC thermal discharge",
            river_name="Hasdeo"),
    Station("WQ-CG-005", "Hasdeo River - Korba Downstream", "Korba",
            StationType.WATER, 22.3300, 82.7200, ZoneType.INDUSTRIAL,
            "Hasdeo river downstream, receives thermal + mining effluent",
            river_name="Hasdeo", factory_proximity_km=0.8),

    # --- Bilaspur (2 stations) ---
    Station("WQ-CG-006", "Arpa River - Bilaspur City", "Bilaspur",
            StationType.WATER, 22.0850, 82.1500, ZoneType.RIVERFRONT,
            "Arpa river flowing through Bilaspur city centre",
            river_name="Arpa"),
    Station("WQ-CG-007", "Arpa River - Bilaspur Industrial", "Bilaspur",
            StationType.WATER, 22.0500, 82.1800, ZoneType.INDUSTRIAL,
            "Arpa river near Uslapur industrial discharge",
            river_name="Arpa", factory_proximity_km=2.0),

    # --- Durg (1 station) ---
    Station("WQ-CG-008", "Sheonath River - Durg Bridge", "Durg",
            StationType.WATER, 21.1800, 81.2700, ZoneType.COMMERCIAL,
            "Sheonath river at Durg city bridge, mixed urban runoff",
            river_name="Sheonath"),

    # --- Raigarh (1 station) ---
    Station("WQ-CG-009", "Kelo River - Raigarh", "Raigarh",
            StationType.WATER, 21.9000, 83.4100, ZoneType.INDUSTRIAL,
            "Kelo river near Raigarh coal washery area",
            river_name="Kelo", factory_proximity_km=1.5),
]


# ---------------------------------------------------------------------------
# NOISE MONITORING STATIONS (9 total)
# Parameters: Leq, Lmax, Lmin, L10, L50, L90, Lden
# ---------------------------------------------------------------------------

NOISE_STATIONS: list[Station] = [
    # --- Raipur (3 stations) ---
    Station("NS-CG-001", "Jaistambh Chowk Noise Monitor", "Raipur",
            StationType.NOISE, 21.2490, 81.6310, ZoneType.COMMERCIAL,
            "Major traffic intersection, peak commercial noise zone"),
    Station("NS-CG-002", "Ambedkar Hospital Silence Zone", "Raipur",
            StationType.NOISE, 21.2400, 81.6200, ZoneType.SILENCE,
            "100m radius silence zone around Ambedkar Hospital"),
    Station("NS-CG-003", "Raipur Railway Station Noise Monitor", "Raipur",
            StationType.NOISE, 21.2350, 81.6350, ZoneType.COMMERCIAL,
            "Near Raipur Junction, train + traffic noise combined"),

    # --- Bhilai (2 stations) ---
    Station("NS-CG-004", "BSP Industrial Noise Monitor", "Bhilai",
            StationType.NOISE, 21.2050, 81.3800, ZoneType.INDUSTRIAL,
            "Near steel plant boundary, continuous industrial noise"),
    Station("NS-CG-005", "Bhilai Sector 6 Residential", "Bhilai",
            StationType.NOISE, 21.2200, 81.4150, ZoneType.RESIDENTIAL,
            "BSP township sector 6, residential ambient monitoring"),

    # --- Korba (1 station) ---
    Station("NS-CG-006", "NTPC Colony Noise Monitor", "Korba",
            StationType.NOISE, 22.3500, 82.7400, ZoneType.INDUSTRIAL,
            "Near NTPC boundary wall, generator and turbine noise"),

    # --- Bilaspur (1 station) ---
    Station("NS-CG-007", "Bilaspur Bus Stand Noise Monitor", "Bilaspur",
            StationType.NOISE, 22.0800, 82.1400, ZoneType.COMMERCIAL,
            "Central bus stand area, peak hour vehicular noise"),

    # --- Durg (1 station) ---
    Station("NS-CG-008", "Durg Clock Tower Noise Monitor", "Durg",
            StationType.NOISE, 21.1900, 81.2850, ZoneType.COMMERCIAL,
            "Main market area near Durg clock tower"),

    # --- Raigarh (1 station) ---
    Station("NS-CG-009", "Raigarh Kotra Road Noise Monitor", "Raigarh",
            StationType.NOISE, 21.8950, 83.3960, ZoneType.COMMERCIAL,
            "Kotra Road commercial area, mining truck route"),
]


# ---------------------------------------------------------------------------
# OCEMS FACTORIES (20 factories for Online Continuous Emission Monitoring)
# Parameters: PM (stack), SO2 (stack), NOx (stack), CO (stack)
# ---------------------------------------------------------------------------

FACTORIES: list[Factory] = [
    # --- Steel & Sponge Iron ---
    Factory("OCEMS-CG-001", "Bhilai Steel Plant (BSP)", "Bhilai",
            21.2094, 81.3784, "Integrated Steel",
            ["PM", "SO2", "NOx", "CO"],
            "SAIL integrated steel plant, largest in CG"),
    Factory("OCEMS-CG-002", "Vandana Global Ltd - Sponge Iron", "Raigarh",
            21.8800, 83.3700, "Sponge Iron",
            ["PM", "SO2", "NOx", "CO"],
            "Sponge iron manufacturing unit"),
    Factory("OCEMS-CG-003", "Godawari Power & Ispat", "Raipur",
            21.3000, 81.5500, "Integrated Steel",
            ["PM", "SO2", "NOx", "CO"],
            "Steel and power producer in Siltara"),
    Factory("OCEMS-CG-004", "Jayaswal Neco Industries", "Raipur",
            21.2700, 81.5200, "Sponge Iron",
            ["PM", "SO2", "NOx", "CO"],
            "Sponge iron and steel casting in Urla"),

    # --- Power Plants ---
    Factory("OCEMS-CG-005", "NTPC Korba Super TPS", "Korba",
            22.3595, 82.7501, "Thermal Power",
            ["PM", "SO2", "NOx", "CO"],
            "2600 MW coal-fired super thermal power station"),
    Factory("OCEMS-CG-006", "NTPC Lara STPS", "Raigarh",
            21.8100, 83.4200, "Thermal Power",
            ["PM", "SO2", "NOx", "CO"],
            "1600 MW supercritical thermal power station"),
    Factory("OCEMS-CG-007", "CSEB Korba East TPS", "Korba",
            22.3400, 82.7100, "Thermal Power",
            ["PM", "SO2", "NOx", "CO"],
            "State electricity board thermal plant"),
    Factory("OCEMS-CG-008", "BALCO Captive Power Plant", "Korba",
            22.3200, 82.6900, "Thermal Power",
            ["PM", "SO2", "NOx", "CO"],
            "Captive power plant for aluminium smelting"),

    # --- Cement ---
    Factory("OCEMS-CG-009", "ACC Jamul Cement Works", "Bhilai",
            21.2500, 81.3200, "Cement",
            ["PM", "SO2", "NOx", "CO"],
            "Cement manufacturing, high particulate emissions"),
    Factory("OCEMS-CG-010", "Lafarge Arasmeta Cement", "Bilaspur",
            22.1200, 82.2300, "Cement",
            ["PM", "SO2", "NOx", "CO"],
            "Cement plant near Bilaspur"),
    Factory("OCEMS-CG-011", "Ambuja Cement - Bhatapara", "Raipur",
            21.7300, 81.9500, "Cement",
            ["PM", "SO2", "NOx", "CO"],
            "Large cement plant near Bhatapara"),
    Factory("OCEMS-CG-012", "UltraTech Cement - Hirmi", "Durg",
            21.4500, 81.4000, "Cement",
            ["PM", "SO2", "NOx", "CO"],
            "Cement grinding unit near Hirmi"),

    # --- Aluminium ---
    Factory("OCEMS-CG-013", "BALCO Aluminium Smelter", "Korba",
            22.3150, 82.6850, "Aluminium Smelting",
            ["PM", "SO2", "NOx", "CO"],
            "Bharat Aluminium Company smelter, fluoride + PM"),

    # --- Coal Mining & Washeries ---
    Factory("OCEMS-CG-014", "SECL Gevra Opencast Mine", "Korba",
            22.2986, 82.5800, "Coal Mining",
            ["PM", "SO2"],
            "Asia's largest opencast coal mine"),
    Factory("OCEMS-CG-015", "SECL Kusmunda Mine", "Korba",
            22.3100, 82.6200, "Coal Mining",
            ["PM", "SO2"],
            "Major opencast coal mine"),
    Factory("OCEMS-CG-016", "Raigarh Coal Washery", "Raigarh",
            21.8700, 83.3800, "Coal Washery",
            ["PM", "SO2"],
            "Coal washing and beneficiation plant"),

    # --- Rice & Agro Processing ---
    Factory("OCEMS-CG-017", "Raipur Rice Mills Cluster", "Raipur",
            21.2400, 81.5900, "Rice Mill",
            ["PM"],
            "Cluster of rice mills generating husk-based PM"),
    Factory("OCEMS-CG-018", "Bilaspur Rice Mill Complex", "Bilaspur",
            22.0600, 82.1600, "Rice Mill",
            ["PM"],
            "Rice husk boilers and dryers"),

    # --- Ferro Alloys ---
    Factory("OCEMS-CG-019", "Chhattisgarh Ferro Alloys", "Durg",
            21.1750, 81.3050, "Ferro Alloys",
            ["PM", "SO2", "NOx", "CO"],
            "Ferro manganese and ferro silicon production"),
    Factory("OCEMS-CG-020", "Raigarh Ferro Alloys", "Raigarh",
            21.9100, 83.3800, "Ferro Alloys",
            ["PM", "SO2", "NOx", "CO"],
            "Ferro alloy manufacturing unit"),
]


# ---------------------------------------------------------------------------
# CPCB/NAAQS Limits for reference (Indian standards)
# ---------------------------------------------------------------------------

NAAQS_LIMITS = {
    # Air Quality (µg/m³ unless noted)
    "PM2.5": {"annual": 40, "daily_24h": 60},
    "PM10": {"annual": 60, "daily_24h": 100},
    "NO2": {"annual": 40, "daily_24h": 80},
    "SO2": {"annual": 50, "daily_24h": 80},
    "CO": {"daily_8h": 2000, "daily_1h": 4000},  # µg/m³
    "O3": {"daily_8h": 100, "daily_1h": 180},
    "NH3": {"annual": 100, "daily_24h": 400},
    "Pb": {"annual": 0.5, "daily_24h": 1.0},
}

WQ_STANDARDS = {
    # Surface water Class C (drinking after conventional treatment)
    "pH": {"min": 6.5, "max": 8.5},
    "DO": {"min": 4.0},          # mg/L
    "BOD": {"max": 3.0},         # mg/L
    "COD": {"max": 25.0},        # mg/L
    "TSS": {"max": 100.0},       # mg/L
    "Turbidity": {"max": 10.0},  # NTU
    "Conductivity": {"max": 2250.0},  # µS/cm
    "Temperature": {"max": 35.0},     # °C
    "Nitrates": {"max": 45.0},        # mg/L
    "Phosphates": {"max": 5.0},       # mg/L
}

CPCB_NOISE_LIMITS = {
    # dB(A) Leq
    "industrial":  {"day": 75, "night": 70},
    "commercial":  {"day": 65, "night": 55},
    "residential": {"day": 55, "night": 45},
    "silence":     {"day": 50, "night": 40},
}

OCEMS_EMISSION_LIMITS = {
    # mg/Nm³ (at 6% O2 for combustion sources)
    "Thermal Power":       {"PM": 30,  "SO2": 200, "NOx": 300, "CO": 150},
    "Integrated Steel":    {"PM": 50,  "SO2": 200, "NOx": 300, "CO": 500},
    "Sponge Iron":         {"PM": 50,  "SO2": 400, "NOx": 300, "CO": 1000},
    "Cement":              {"PM": 30,  "SO2": 100, "NOx": 300, "CO": 150},
    "Aluminium Smelting":  {"PM": 50,  "SO2": 200, "NOx": 300, "CO": 300},
    "Coal Mining":         {"PM": 150, "SO2": 200},
    "Coal Washery":        {"PM": 150, "SO2": 200},
    "Rice Mill":           {"PM": 150},
    "Ferro Alloys":        {"PM": 50,  "SO2": 400, "NOx": 300, "CO": 1000},
}


# ---------------------------------------------------------------------------
# Convenience accessors
# ---------------------------------------------------------------------------

ALL_STATIONS = AIR_STATIONS + WATER_STATIONS + NOISE_STATIONS

STATIONS_BY_CITY: dict[str, list[Station]] = {}
for _s in ALL_STATIONS:
    STATIONS_BY_CITY.setdefault(_s.city, []).append(_s)

STATIONS_BY_ID: dict[str, Station] = {s.station_id: s for s in ALL_STATIONS}
FACTORIES_BY_ID: dict[str, Factory] = {f.factory_id: f for f in FACTORIES}


# Chhattisgarh bounding box (used by simulator)
CG_BOUNDING_BOX = {
    "lat_min": 17.78,
    "lat_max": 24.12,
    "lon_min": 80.24,
    "lon_max": 84.40,
}

# City centroids for reference
CITY_CENTROIDS = {
    "Raipur":   (21.2514, 81.6296),
    "Bhilai":   (21.2167, 81.4278),
    "Korba":    (22.3490, 82.6830),
    "Bilaspur": (22.0796, 82.1391),
    "Durg":     (21.1904, 81.2849),
    "Raigarh":  (21.8974, 83.3950),
}


def get_stations_for_type(stype: StationType) -> list[Station]:
    """Return all stations of a given type."""
    return [s for s in ALL_STATIONS if s.station_type == stype]


def get_factories_for_city(city: str) -> list[Factory]:
    """Return all factories in a given city."""
    return [f for f in FACTORIES if f.city == city]


if __name__ == "__main__":
    print(f"Total stations: {len(ALL_STATIONS)}")
    print(f"  Air:   {len(AIR_STATIONS)}")
    print(f"  Water: {len(WATER_STATIONS)}")
    print(f"  Noise: {len(NOISE_STATIONS)}")
    print(f"Factories: {len(FACTORIES)}")
    print()
    for city, stations in STATIONS_BY_CITY.items():
        print(f"  {city}: {len(stations)} stations")
    print()
    for city in CITY_CENTROIDS:
        facs = get_factories_for_city(city)
        print(f"  {city}: {len(facs)} factories")
