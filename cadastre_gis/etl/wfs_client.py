"""
Resilient GeoServer Web Feature Service (WFS) Client.
Supports WFS 1.0.0, 1.1.0, and 2.0.0 protocols with CQL filtering,
exponential backoff, authentication, and paginated feature fetching.
"""

import xml.etree.ElementTree as ET
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from cadastre_gis.config import AUTH_KEY, REQUEST_TIMEOUT, USER_AGENT, WFS_BASE_URL, WFS_LAYER_NAME


class CadastreWFSClient:
    """
    Client for interacting with cadastral GeoServer WFS services.
    """

    def __init__(
        self,
        base_url: str | None = None,
        auth_key: str | None = None,
        layer_name: str | None = None,
        timeout: int = REQUEST_TIMEOUT,
    ):
        self.base_url = (base_url or WFS_BASE_URL).rstrip("?")
        self.auth_key = auth_key if auth_key is not None else AUTH_KEY
        self.layer_name = layer_name or WFS_LAYER_NAME
        self.timeout = timeout

        self.session = requests.Session()
        retries = Retry(total=4, backoff_factor=1.0, status_forcelist=[429, 500, 502, 503, 504], raise_on_status=False)
        adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=20)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update(
            {"User-Agent": USER_AGENT, "Accept": "application/json, application/xml, text/xml, */*"}
        )

    def get_capabilities(self, version: str = "1.1.0") -> str:
        """
        Fetch WFS GetCapabilities document.
        """
        params = {"SERVICE": "WFS", "VERSION": version, "REQUEST": "GetCapabilities"}
        if self.auth_key:
            params["authkey"] = self.auth_key

        resp = self.session.get(self.base_url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.text

    def list_feature_types(self) -> list[str]:
        """
        Parse layer/FeatureType names from GetCapabilities XML.
        """
        xml_content = self.get_capabilities()
        root = ET.fromstring(xml_content)
        layers = []
        for elem in root.iter():
            if elem.tag.endswith("FeatureType"):
                for child in elem:
                    if child.tag.endswith("Name") and child.text:
                        layers.append(child.text)
        return sorted(set(layers))

    def fetch_parcels_geojson(
        self, ko_id: str | int = "57062", cql_filter: str | None = None, max_features: int = 5000, start_index: int = 0
    ) -> dict[str, Any]:
        """
        Fetch cadastral parcels as GeoJSON FeatureCollection.
        """
        filter_expr = cql_filter or f"KO='{ko_id}'"
        params = {
            "SERVICE": "WFS",
            "VERSION": "1.1.0",
            "REQUEST": "GetFeature",
            "TYPENAME": self.layer_name,
            "CQL_FILTER": filter_expr,
            "outputFormat": "application/json",
            "maxFeatures": str(max_features),
            "startIndex": str(start_index),
        }
        if self.auth_key:
            params["authkey"] = self.auth_key

        resp = self.session.get(self.base_url, params=params, timeout=self.timeout * 2)
        resp.raise_for_status()
        return resp.json()
