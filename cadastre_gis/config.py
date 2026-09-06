"""
Configuration management for CadastreGIS.
Reads settings from environment variables and local .env files.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Base paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Geographic & Administrative Defaults (Donji Žabar, Republika Srpska)
DEFAULT_CITY_ID = os.getenv("CADASTRE_CITY_ID", "35")
DEFAULT_CITY_NAME = os.getenv("CADASTRE_CITY_NAME", "Доњи Жабар")
DEFAULT_CITY_NAME_LATIN = os.getenv("CADASTRE_CITY_NAME_LATIN", "Donji Zabar")
DEFAULT_KO_ID = os.getenv("CADASTRE_KO_ID", "57062")

# WFS / Web Feature Service Configuration
WFS_BASE_URL = os.getenv("CADASTRE_WFS_URL", "https://ekatastar.rgurs.org/geoserver/WS_RPJ_RS/wfs")
WFS_LAYER_NAME = os.getenv("CADASTRE_WFS_LAYER", "WS_RPJ_RS:OL_PARCELE_JAVNI_UVID")
# Auth key should be supplied via .env or CADASTRE_AUTH_KEY environment variable.
AUTH_KEY = os.getenv("CADASTRE_AUTH_KEY", "")

# e-Katastar REST API Configuration
OWNER_API_BASE = os.getenv("CADASTRE_OWNER_API_BASE", "https://ekatastar.rgurs.org/api/kc")

# Concurrency & Network Configuration
MAX_WORKER_THREADS = int(os.getenv("CADASTRE_MAX_THREADS", "16"))
REQUEST_TIMEOUT = int(os.getenv("CADASTRE_REQUEST_TIMEOUT", "15"))
USER_AGENT = os.getenv(
    "CADASTRE_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
)

# Data Paths
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_DATASET = DATA_DIR / "donji_zabar_wgs84.geojson"

# Coordinate Reference System Defaults
# MGI 1901 Gauss-Kruger Zone 6 with 7-parameter Balkan Helmert shift
MGI_ZONE_6_PROJ4 = (
    "+proj=tmerc +lat_0=0 +lon_0=18 +k=0.9999 +x_0=6500000 +y_0=0 "
    "+ellps=bessel +towgs84=682,-203,480,0,0,0,0 +units=m +no_defs"
)
EPSG_MGI_ZONE_6 = "EPSG:31276"
EPSG_WGS84 = "EPSG:4326"
EPSG_WEB_MERCATOR = "EPSG:3857"

# Web Application Settings
WEB_HOST = os.getenv("CADASTRE_WEB_HOST", "127.0.0.1")
WEB_PORT = int(os.getenv("CADASTRE_WEB_PORT", "5000"))
WEB_DEBUG = os.getenv("CADASTRE_WEB_DEBUG", "false").lower() in ("true", "1", "yes")
