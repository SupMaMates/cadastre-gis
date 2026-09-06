"""
High-Precision Coordinate Reference System (CRS) Transformer.

Specialized for Balkan Cadastral Coordinate Systems:
- MGI 1901 / Gauss-Kruger Zone 5 (EPSG:31275, central meridian 15°E)
- MGI 1901 / Gauss-Kruger Zone 6 (EPSG:31276, central meridian 18°E - Bosnia and Herzegovina, Serbia)
- MGI 1901 / Gauss-Kruger Zone 7 (EPSG:31277, central meridian 21°E - Eastern Serbia)
- Incorporates the official/military 7-parameter Helmert transformation:
  +towgs84=682,-203,480,0,0,0,0
- Converts to/from WGS84 (EPSG:4326) and Web Mercator (EPSG:3857).
"""

from typing import Any, ClassVar

from pyproj import CRS, Transformer
from shapely import wkt
from shapely.geometry import mapping, shape
from shapely.ops import transform


class BalkanCrsTransformer:
    """
    Precision transformer between Balkan Gauss-Kruger projections and global reference systems.
    """

    MGI_PROJ4_TEMPLATES: ClassVar[dict[int, str]] = {
        31275: (
            "+proj=tmerc +lat_0=0 +lon_0=15 +k=0.9999 +x_0=5500000 +y_0=0 "
            "+ellps=bessel +towgs84=682,-203,480,0,0,0,0 +units=m +no_defs"
        ),
        31276: (
            "+proj=tmerc +lat_0=0 +lon_0=18 +k=0.9999 +x_0=6500000 +y_0=0 "
            "+ellps=bessel +towgs84=682,-203,480,0,0,0,0 +units=m +no_defs"
        ),
        31277: (
            "+proj=tmerc +lat_0=0 +lon_0=21 +k=0.9999 +x_0=7500000 +y_0=0 "
            "+ellps=bessel +towgs84=682,-203,480,0,0,0,0 +units=m +no_defs"
        ),
    }

    def __init__(self, source_epsg: int = 31276, target_epsg: int = 4326):
        """
        Initialize the transformer.
        :param source_epsg: EPSG code of source projection (default 31276 - MGI Zone 6)
        :param target_epsg: EPSG code of target projection (default 4326 - WGS84)
        """
        self.source_epsg = source_epsg
        self.target_epsg = target_epsg

        # Source CRS definition with datum shift
        if source_epsg in self.MGI_PROJ4_TEMPLATES:
            self.source_crs = CRS.from_proj4(self.MGI_PROJ4_TEMPLATES[source_epsg])
        else:
            self.source_crs = CRS.from_epsg(source_epsg)

        # Target CRS definition
        self.target_crs = CRS.from_epsg(target_epsg)

        # Forward transformer: source -> target
        self.forward_transformer = Transformer.from_crs(self.source_crs, self.target_crs, always_xy=True)

        # Inverse transformer: target -> source
        self.inverse_transformer = Transformer.from_crs(self.target_crs, self.source_crs, always_xy=True)

    def transform_point(self, x: float, y: float) -> tuple[float, float]:
        """
        Transform a single point (x, y) from source CRS to (lon, lat) in target CRS.
        """
        lon, lat = self.forward_transformer.transform(x, y)
        return lon, lat

    def transform_point_inverse(self, lon: float, lat: float) -> tuple[float, float]:
        """
        Transform a single point (lon, lat) from target CRS to (x, y) in source CRS.
        """
        x, y = self.inverse_transformer.transform(lon, lat)
        return x, y

    def transform_geometry(self, geom_dict_or_shapely: Any, precision: int = 6) -> dict[str, Any]:
        """
        Transform a GeoJSON geometry dict or Shapely geometry to target CRS.
        Coordinates are rounded to specified decimal places (default 6 ~ 10cm).
        """
        if isinstance(geom_dict_or_shapely, dict):
            s_geom = shape(geom_dict_or_shapely)
        else:
            s_geom = geom_dict_or_shapely

        transformed_s = transform(lambda x, y, z=None: self.forward_transformer.transform(x, y), s_geom)

        m = mapping(transformed_s)
        m["coordinates"] = self._round_coords(m["coordinates"], precision)
        return m

    def transform_wkt(self, wkt_str: str, precision: int = 6) -> dict[str, Any]:
        """
        Parse WKT string and transform to target CRS GeoJSON dict.
        """
        s_geom = wkt.loads(wkt_str)
        return self.transform_geometry(s_geom, precision=precision)

    @classmethod
    def _round_coords(cls, coords: Any, precision: int) -> Any:
        if not coords:
            return coords
        if isinstance(coords[0], (int, float)):
            return [round(coords[0], precision), round(coords[1], precision)]
        return [cls._round_coords(sub, precision) for sub in coords]


def reproject_geojson_collection(
    geojson_data: dict[str, Any],
    source_epsg: int = 31276,
    target_epsg: int = 4326,
    precision: int = 6,
    remove_raw_html: bool = True,
) -> dict[str, Any]:
    """
    Reproject an entire GeoJSON FeatureCollection with precision coordinate rounding
    and optional cleaning of heavy debug/HTML attributes.
    """
    transformer = BalkanCrsTransformer(source_epsg=source_epsg, target_epsg=target_epsg)
    features = geojson_data.get("features", [])
    transformed_features = []

    for feat in features:
        props = feat.get("properties", {}).copy()
        if remove_raw_html and "REGISTRY_RAW" in props:
            del props["REGISTRY_RAW"]

        geom = feat.get("geometry")
        new_geom = transformer.transform_geometry(geom, precision=precision) if geom else None

        transformed_features.append(
            {
                "type": "Feature",
                "id": feat.get("id") or str(props.get("PARCELID", "")),
                "geometry": new_geom,
                "properties": props,
            }
        )

    return {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": transformed_features,
    }
