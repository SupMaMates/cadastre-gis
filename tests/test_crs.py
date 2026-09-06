"""
Unit tests for Coordinate Reference System (CRS) transformations and KML generation.
"""

import pytest

from cadastre_gis.crs.kml import export_parcel_to_kml
from cadastre_gis.crs.transformer import BalkanCrsTransformer, reproject_geojson_collection


def test_balkan_crs_transformation_point():
    """Test point projection from MGI Zone 6 (EPSG:31276) to WGS84 (EPSG:4326)."""
    transformer = BalkanCrsTransformer(source_epsg=31276, target_epsg=4326)

    # Ground truth: Donji Žabar sample coordinate
    mgi_x = 6551297.92
    mgi_y = 4978896.77
    lon, lat = transformer.transform_point(mgi_x, mgi_y)

    # Donji Žabar is located at approx 44.95° N, 18.64° E
    assert pytest.approx(lon, abs=0.001) == 18.6450
    assert pytest.approx(lat, abs=0.001) == 44.9527


def test_balkan_crs_inverse_transformation():
    """Test round-trip point projection."""
    transformer = BalkanCrsTransformer(source_epsg=31276, target_epsg=4326)

    orig_x = 6551297.92
    orig_y = 4978896.77
    lon, lat = transformer.transform_point(orig_x, orig_y)
    back_x, back_y = transformer.transform_point_inverse(lon, lat)

    assert pytest.approx(back_x, abs=0.05) == orig_x
    assert pytest.approx(back_y, abs=0.05) == orig_y


def test_geometry_transformation():
    """Test transforming a GeoJSON polygon geometry."""
    transformer = BalkanCrsTransformer(source_epsg=31276, target_epsg=4326)

    polygon_mgi = {
        "type": "Polygon",
        "coordinates": [
            [
                [6551862.17, 4976501.02],
                [6551836.74, 4976505.46],
                [6551826.52, 4976409.47],
                [6551846.72, 4976405.92],
                [6551862.17, 4976501.02],
            ]
        ],
    }

    wgs_geom = transformer.transform_geometry(polygon_mgi, precision=6)
    assert wgs_geom["type"] == "Polygon"
    coords = wgs_geom["coordinates"][0]
    assert len(coords) == 5

    # Check longitude and latitude are in WGS84 range
    for pt in coords:
        assert 18.0 <= pt[0] <= 19.0
        assert 44.0 <= pt[1] <= 46.0


def test_reproject_geojson_collection():
    """Test reprojecting an entire FeatureCollection."""
    fc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "1",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[6551862.17, 4976501.02], [6551836.74, 4976505.46], [6551862.17, 4976501.02]]],
                },
                "properties": {"parcel_id": "1", "REGISTRY_RAW": "<div>dummy html</div>"},
            }
        ],
    }

    result = reproject_geojson_collection(fc, source_epsg=31276, target_epsg=4326, remove_raw_html=True)
    assert result["type"] == "FeatureCollection"
    feat = result["features"][0]
    assert "REGISTRY_RAW" not in feat["properties"]
    assert feat["geometry"]["coordinates"][0][0][0] < 100.0  # WGS84 lon, not MGI meters


def test_kml_export():
    """Test generating a compliant KML polygon string."""
    feature = {
        "type": "Feature",
        "id": "1376_2",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [[18.6450, 44.9527], [18.6460, 44.9527], [18.6460, 44.9537], [18.6450, 44.9537], [18.6450, 44.9527]]
            ],
        },
        "properties": {
            "parcel_id": "1376/2",
            "area_sqm": 1250,
            "pl_broj": "450",
            "ko_naziv": "Donji Žabar",
            "owners": [{"name": "Jovanović (Petra) Marko", "share_raw": "1/1"}],
            "parts": [{"usage_type": "Njiva 3. klase", "area_sqm": 1250}],
        },
    }

    kml = export_parcel_to_kml(feature)
    assert "<?xml" in kml
    assert "<kml" in kml
    assert "Parcela 1376/2" in kml
    assert "<LinearRing>" in kml
    assert "18.645,44.9527,0" in kml
