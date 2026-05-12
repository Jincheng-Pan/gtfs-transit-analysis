# gtfs-transit-analysis
A lightweight Python project for analysing public transport service supply from GTFS static feeds.

This project was designed for GTFS-based transport planning analysis, including route-level service frequency, peak-period service, route geometry, travel time, and before/after route comparison workflows.

## Features

- Load GTFS static feeds safely with ID fields treated as strings.
- Select representative weekday services **by route**, avoiding the loss of train, ferry, regional, and special route groups caused by using one global `service_id`.
- Analyse each route and direction/headsign separately.
- Calculate:
  - first and last departure
  - daily trip count
  - daily average headway
  - AM peak trips and headway
  - PM peak trips and headway
  - approximate route length
  - direct end-to-end distance
  - circuity
  - in-vehicle time
  - average travel time
- Export representative route OD stop-pair travel-time tables.
- Compare before/after OD travel-time tables.

## Project structure

```text
gtfs-transit-analysis/
├── config/
│   └── example_config.yaml
├── data/
│   ├── raw/          # ignored by Git; place GTFS feeds here locally
│   └── processed/    # ignored by Git
├── results/          # ignored by Git
├── scripts/
│   └── analyse_feed.py
├── src/
│   └── gtfs_transit_analysis/
│       ├── analysis.py
│       ├── cli.py
│       ├── compare.py
│       ├── geometry.py
│       ├── io.py
│       └── services.py
├── .gitignore
├── pyproject.toml
├── README.md
└── requirements.txt
```

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

## Data preparation

Download or obtain a GTFS static feed and place the extracted `.txt` files in a local folder such as:

```text
data/raw/SEQ_SCH_GTFS/
├── routes.txt
├── trips.txt
├── stop_times.txt
├── stops.txt
├── calendar.txt
└── ...
```

Do **not** upload raw GTFS files to GitHub unless the data licence clearly permits redistribution. This repository is configured to ignore `data/raw/`, `data/processed/`, and `results/`.

## Usage

### 1. Analyse a full GTFS feed

```bash
gtfs-transit-analysis analyse \
  --gtfs data/raw/SEQ_SCH_GTFS \
  --output results/route_service_analysis.csv
```

Or:

```bash
python scripts/analyse_feed.py analyse \
  --gtfs data/raw/SEQ_SCH_GTFS \
  --output results/route_service_analysis.csv
```

### 2. Export OD travel times for a representative route trip

```bash
gtfs-transit-analysis route-od \
  --gtfs data/raw/SEQ_SCH_GTFS \
  --route 125 \
  --direction 0 \
  --output results/route_125_direction_0_od.csv
```

### 3. Compare old and new OD travel times

```bash
gtfs-transit-analysis compare-od \
  --old results/old_route_od.csv \
  --new results/new_route_od.csv \
  --output results/od_comparison.csv
```

## Output columns

The main analysis output includes:

| Column | Meaning |
|---|---|
| `route_id` | GTFS route ID |
| `route_name` | Route short name |
| `direction_headsign` | Direction based on `trip_headsign` |
| `selected_service_id` | Representative weekday service selected for that route |
| `representative_trip_id` | Trip used for geometry and in-vehicle time |
| `first_departure` | First departure time |
| `last_departure` | Last departure time |
| `trips_daily` | Number of trips in the selected representative weekday service |
| `headway_daily_min` | Average daily headway based on operating span |
| `trips_am_peak` | Trips departing during 07:00-09:00 |
| `headway_am_peak_min` | AM peak average headway |
| `trips_pm_peak` | Trips departing during 16:00-18:00 |
| `headway_pm_peak_min` | PM peak average headway |
| `route_length_km_approx` | Approximate route length using consecutive stop-to-stop great-circle distances |
| `direct_distance_km` | Straight-line distance between first and last stop |
| `circuity` | `route_length_km_approx / direct_distance_km` |
| `in_vehicle_time_min` | Representative trip in-vehicle time |
| `avg_travel_time_min` | `in_vehicle_time + headway_daily / 2` |

## Method notes

1. **GTFS identifiers are strings.** The loader reads GTFS tables with `dtype=str` to avoid merge errors involving fields such as `stop_id`.
2. **Representative weekday service is selected by route.** This is more robust than selecting a single global `service_id`, because multi-modal feeds often use different service IDs for bus, train, ferry, regional, and replacement services.
3. **Direction is based on `trip_headsign`.** This avoids assuming that `direction_id = 0` always means inbound or outbound.
4. **Route length is approximate.** It uses consecutive stop-to-stop great-circle distances. If `shapes.txt` is available and high precision is required, a future improvement would calculate shape-based distance instead.
5. **Average travel time is simplified.** It uses in-vehicle time plus half of the daily average headway as a waiting-time approximation.

## Example research applications

- Public transport service supply assessment
- Route restructuring before/after comparison
- Bus network redesign evaluation
- GTFS-based transit accessibility analysis
- LLM-assisted public transport planning and decision support

## Licence and data disclaimer

This repository is intended to publish code and derived analysis workflows. Raw GTFS data should not be redistributed unless permitted by the relevant data provider's licence.
