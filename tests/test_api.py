"""
Integration tests for the Flask Web GIS and REST API endpoints.
"""

import pytest

from cadastre_gis.config import DEFAULT_DATASET
from cadastre_gis.web.app import create_app


@pytest.fixture
def client():
    app = create_app(dataset_path=DEFAULT_DATASET)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_index_route(client):
    """Test web application root page returns HTML."""
    res = client.get("/")
    assert res.status_code == 200
    assert b"CadastreGIS" in res.data
    assert b"leaflet-map" in res.data


def test_api_health(client):
    """Test health check API endpoint."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert data["parcels_count"] == 4172


def test_api_meta(client):
    """Test metadata API endpoint."""
    res = client.get("/api/meta")
    assert res.status_code == 200
    data = res.get_json()
    assert "bounds" in data
    assert "center" in data
    assert data["crs"] == "EPSG:4326"


def test_api_parcels_filter(client):
    """Test parcel filtering by search query and usage category."""
    res = client.get("/api/parcels?search=1&limit=5")
    assert res.status_code == 200
    data = res.get_json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) <= 5


def test_api_parcel_detail(client):
    """Test retrieving a single parcel by ID."""
    res = client.get("/api/parcels/1")
    assert res.status_code == 200
    data = res.get_json()
    assert data["properties"]["broj"] == "1"
    assert "owners" in data["properties"]
    assert "parts" in data["properties"]


def test_api_parcel_kml_download(client):
    """Test downloading styled KML for a parcel."""
    res = client.get("/api/parcels/1/kml")
    assert res.status_code == 200
    assert "google-earth.kml+xml" in res.content_type
    assert b"<kml" in res.data
    assert b"Parcela 1" in res.data


def test_api_analytics(client):
    """Test analytics report endpoint."""
    res = client.get("/api/analytics?top_n=5")
    assert res.status_code == 200
    data = res.get_json()
    assert "metrics" in data
    assert "gini_coefficient" in data["metrics"]
    assert "top_owners" in data
    assert "lorenz_curve" in data
