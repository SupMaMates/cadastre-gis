# CadastreGIS • Advanced Cadastral & Land Registry Intelligence Platform

[![Python 3.9+](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Live Demo](https://img.shields.io/badge/demo-live%20on%20GitHub%20Pages-success.svg?style=flat&logo=github)](https://supmamates.github.io/cadastre-gis/)
[![Tests](https://img.shields.io/badge/tests-23%20passed%20%28100%25%29-brightgreen.svg)](https://pytest.org/)
[![Linter: Ruff](https://img.shields.io/badge/linter-ruff%20clean-black.svg)](https://github.com/astral-sh/ruff)
[![GeoJSON](https://img.shields.io/badge/RFC_7946-GeoJSON%20Compliant-orange.svg)](https://datatracker.ietf.org/doc/html/rfc7946)
[![License: MIT](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)

🌐 **Live Interactive Web GIS & Analytics Demo**: [https://supmamates.github.io/cadastre-gis/](https://supmamates.github.io/cadastre-gis/)

An enterprise-grade, high-precision GIS, econometric analysis, and web mapping platform designed for cadastral municipalities across the Balkans, Republika Srpska, Bosnia and Herzegovina, and Serbia (starting with **Donji Žabar, K.O. 57062**).

CadastreGIS bridges the gap between fragmented institutional registries (GeoServer WFS + e-Katastar HTML portals), military datum projections (MGI Gauss-Kruger Zone 6), modern geospatial web standards (WGS84, Leaflet), and econometric landholding analytics (Gini, Palma, Theil, HHI, and fragmentation indices).

---

## 🌟 Key Capabilities & Architectural Highlights

### 1. High-Precision Coordinate Reference System (CRS) Engine
* **Balkan Gauss-Kruger Support**: Full bidirectional reprojection between MGI 1901 Gauss-Kruger zones (Zone 5 EPSG:31275, Zone 6 EPSG:31276, Zone 7 EPSG:31277) and global systems (WGS84 EPSG:4326, Web Mercator EPSG:3857).
* **Official 7-Parameter Helmert Shift**: Seamlessly applies the Balkan military/geodetic datum transformation:
  ```text
  +towgs84=682,-203,480,0,0,0,0
  ```
  ensuring centimeter-level polygon alignment when overlaid onto modern satellite imagery (Google Maps, Esri World Imagery).
* **RFC 7946 Compliance**: Normalizes coordinates to WGS84 `[longitude, latitude]` with standard 6-decimal precision (~10cm accuracy) and strips heavy redundant HTML blobs, reducing dataset memory footprint from **37.3 MB down to 5.45 MB** (over 85% size reduction).
* **Google Earth KML 2.2 Exporter**: One-click generation of styled KML files with custom polygon borders, fill transparencies, and rich HTML ownership tables for mobile GPS and desktop Google Earth.

### 2. Cadastre Econometrics & Inequality Analytics ("God-Mode")
* **Land Concentration Metrics**:
  * **Gini Coefficient**: Robust calculation of land wealth inequality (0.8142 private wealth Gini in Donji Žabar).
  * **Palma Ratio**: Measures the ratio of land owned by the top 10% vs. the bottom 40% (10.37x).
  * **Theil Entropy Index & HHI**: Measures structural market and land concentration.
  * **Top Percentile Shares**: Quantifies land owned by Top 1%, Top 5%, Top 10%, and Top 20% of owners.
  * **Lorenz Curve Coordinates**: Generates mathematical coordinates comparing actual cumulative land distributions against the 45° line of absolute equality.
* **Lineage, Patronymics & Clan Dominance**:
  * Specialized parsing of Balkan naming conventions: `SURNAME (FATHER) FIRSTNAME`.
  * Gender heuristics (with exceptions for names like Nikola, Luka, Ilija, Sava, Nemanja).
  * Clan aggregation (`surname | father` household lineage clusters) and Shannon entropy of name diversity.
* **Agronomic Soil Capability & Land Use**:
  * Automatic extraction of cadastral land quality classes (1st to 8th class, e.g., *"Njiva 3. klase"*).
  * Weighted average soil capability score across agricultural parcels.
  * Functional categorization: Agricultural, Residential, Yard, Forest, Infrastructure, and Other.

### 3. Land Fragmentation & Inheritance Gridlock Diagnostics
* **Effective Number of Owners ($N_{\text{eff}}$)**: Applies the inverse Herfindahl index $N_{\text{eff}} = 1 / \sum s_i^2$ to distinguish balanced co-ownership from symbolic micro-shares.
* **"Inheritance Nightmare" Detector**: Flags parcels paralyzed by fractional generational inheritances (e.g., individual shares smaller than $1/20$ or $1/64$).
* **Registry Quality Auditor**: Identifies cadastral records where the sum of ownership shares deviates from $1.0$ ($\sum s_i \neq 1.0$), pinpointing disputed titles or unrecorded probate proceedings.

### 4. Interactive Production Web GIS Platform
* **Dual-View Interface**:
  * **Interactive Map View**: High-performance vector rendering of 4,172 parcels using Leaflet, with 4 base layers (Esri Satellite, CartoDB Dark Matter, CartoDB Positron, OpenStreetMap).
  * **Choropleth Themes**:
    1. *Standard Cadastral Boundaries*
    2. *Land Use Category (Agricultural, Residential, Yard, Forest, Infrastructure)*
    3. *Fragmentation Level (Single Owner vs 2-3 vs 4-6 vs 7+ Co-owners)*
    4. *Ownership Type (Private Individual vs State/Municipality/Corporation)*
    5. *Area Heatmap (Size distribution)*
  * **Live Instant Search**: Sub-millisecond search across parcel IDs (e.g., `1376/2`), title possession sheets (`PL 615`), and owner names.
  * **Slide-over Parcel Inspector**: Instant inspection drawer with ownership table, share percentages, land parts, GPS coordinate copying, and KML export.
  * **God-Mode Analytics Dashboard**: 6 interactive Chart.js visualizations (Lorenz Curve, Top Landowners, Land Use Donut, Clan Wealth, Fragmentation Breakdown, Soil Quality) and tabbed leaderboards.

---

## 🏛️ System Architecture

```
GIS/
├── cadastre_gis/                    # Core Python Package
│   ├── __init__.py                  # Package exports & versioning
│   ├── config.py                    # Environment settings (.env) & geodetic constants
│   ├── crs/                         # Precision Coordinate Reference Systems
│   │   ├── __init__.py
│   │   ├── transformer.py           # Balkan Gauss-Kruger <-> WGS84 with 7-param Helmert
│   │   └── kml.py                   # Styled KML 2.2 generator
│   ├── etl/                         # Data Ingestion & Scraper Pipeline
│   │   ├── __init__.py
│   │   ├── wfs_client.py            # GeoServer WFS client (1.1.0/2.0.0) with retries
│   │   ├── rgurs_client.py          # e-Katastar HTML scraper for ownership & parts
│   │   └── pipeline.py              # End-to-end WFS + concurrent enrichment runner
│   ├── analytics/                   # Econometric & Statistical Engine
│   │   ├── __init__.py
│   │   ├── inequality.py            # Gini, Theil, HHI, Palma ratio, Lorenz curve
│   │   ├── fragmentation.py         # Effective owners, micro-shares, anomaly detector
│   │   ├── demographics.py          # Balkan naming, gender, clans, Shannon entropy
│   │   ├── land_use.py              # Agronomic classification & weighted land quality
│   │   └── engine.py                # Comprehensive report generator (JSON, CSV, Rich CLI)
│   ├── web/                         # Interactive Web GIS Application
│   │   ├── __init__.py
│   │   ├── app.py                   # Flask REST API with spatial querying & caching
│   │   ├── static/
│   │   │   ├── css/app.css          # Coherent CSS design tokens & themes (dark/light)
│   │   │   └── js/
│   │   │       ├── map.js           # Leaflet map, vector choropleths, parcel inspector
│   │   │       └── dashboard.js     # Chart.js analytics & Lorenz curve
│   │   └── templates/
│   │       └── index.html           # Modern responsive Web GIS UI
│   └── cli.py                       # Unified CLI interface
├── data/                            # Curated Datasets
│   ├── donji_zabar_wgs84.geojson    # Canonical WGS84 GeoJSON (4,172 parcels, ~5.45MB)
│   └── raw_probes/                  # Archived GeoServer capabilities XML probes
├── tests/                           # Comprehensive Pytest Suite (23 tests)
│   ├── test_crs.py                  # Geodetic transformation & Helmert shift tests
│   ├── test_analytics.py            # Gini, Palma, fragmentation, demographics tests
│   ├── test_etl.py                  # HTML parsers & sub-parcel matching tests
│   └── test_api.py                  # Flask endpoints & KML download tests
├── .env.example                     # Environment template
├── .gitignore                       # Clean Git configuration
├── pyproject.toml                   # Modern PEP 621 packaging
├── requirements.txt                 # Production dependencies
└── requirements-dev.txt             # Development & testing dependencies
```

---

## 🚀 Quickstart & Installation

### 1. Prerequisites
- Python 3.9 or higher (tested on Python 3.10, 3.11, 3.12, 3.13)
- Git

### 2. Setup Virtual Environment
```bash
python -m venv .venv

# Windows:
.venv\Scripts\activate

# Linux / macOS:
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
pip install -e .
```

### 4. Configure Environment Variables (Optional)
Copy the template file to configure optional credentials:
```bash
cp .env.example .env
```

---

## 💻 CLI Usage

CadastreGIS provides a unified command line interface (`cadastre-gis`):

### 1. Launch the Interactive Web GIS Server
```bash
cadastre-gis web --port 5000
```
Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your web browser.

### 2. Run Econometric & Land Inequality Analysis
```bash
# Print summary to terminal
cadastre-gis analyze --top 15

# Export full CSVs and report.json to a directory:
cadastre-gis analyze --top 20 --export-dir reports/
```

### 3. High-Precision CRS Transformation
```bash
# Transform from MGI Gauss-Kruger Zone 6 (EPSG:31276) to standard WGS84 (EPSG:4326)
cadastre-gis transform input_mgi.geojson output_wgs84.geojson --from-epsg 31276 --to-epsg 4326
```

### 4. Export Parcel to Google Earth KML
```bash
cadastre-gis kml 1376/2 --output parcel_1376_2.kml
```

### 5. Display Dataset & System Info
```bash
cadastre-gis info
```

---

## 📡 RESTful API Documentation

| Endpoint | Method | Description |
|---|---|---|
| `GET /` | HTML | Serves the single-page Web GIS application |
| `GET /api/health` | JSON | Service status, parcel count, and dataset info |
| `GET /api/meta` | JSON | Municipality name, bounds, centroid, and CRS |
| `GET /api/parcels` | JSON | GeoJSON FeatureCollection with query filtering (`search`, `usage`, `coowned`, `anomalies`, `limit`) |
| `GET /api/parcels/<id>` | JSON | Detailed parcel info, ownership roster, and land use parts |
| `GET /api/parcels/<id>/kml` | XML | Downloads styled KML 2.2 polygon for Google Earth |
| `GET /api/analytics` | JSON | Econometric KPIs, Gini, Palma, Lorenz points, top clans |
| `GET /api/export` | File | Export filtered parcels as GeoJSON (`?format=geojson`) or CSV (`?format=csv`) |

---

## 🌐 Free Live Hosting & Deployment

The platform is designed with dual-mode execution (Dynamic Python Flask server OR zero-server static CDN deployment).

### 1. GitHub Pages (Free & Instant, Zero Server Maintenance)
The static web application bundle is pre-compiled under `docs/`. The repository includes an automated GitHub Actions deployment workflow (`.github/workflows/deploy.yml`).
1. In repository **Settings** → **Pages**:
2. Under **Build and deployment** → **Source**, select **GitHub Actions** (or Deploy from branch `main`, folder `/docs`).
3. Your Web GIS is immediately live globally at:
   ```
   https://<your-username>.github.io/cadastre-gis/
   ```
All vector map layers, choropleths, parcel search, dynamic Chart.js econometrics, browser-side KML generators, and CSV/GeoJSON exports run 100% client-side with 0 server costs and 0 cold starts!

### 2. Render.com (Free Web Service - Dynamic Flask API)
The project includes a turnkey `render.yaml` and `Procfile`.
1. Fork or push to GitHub.
2. Sign in to [Render](https://render.com/) and click **New** → **Blueprint**.
3. Select this repository. Render will automatically detect `render.yaml` and launch the dynamic Python service on the free tier.

### 3. Vercel (Free Static Hosting)
The project includes `vercel.json` configured for the `docs` directory:
```bash
npx vercel --prod
```

---

## 🧪 Testing & Validation

Run the complete test suite:
```bash
pytest -v
```

Linting and code formatting:
```bash
ruff check .
ruff format .
```

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
