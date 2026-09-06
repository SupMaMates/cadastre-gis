"""
e-Katastar Registry Scraper & Parser.
Extracts title sheet numbers, ownership records (shares and names), land use parts,
and data freshness replication timestamps from e-Katastar HTML endpoints.
"""

import re
import urllib.parse
from typing import Any

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from cadastre_gis.config import DEFAULT_CITY_ID, DEFAULT_CITY_NAME, OWNER_API_BASE, REQUEST_TIMEOUT, USER_AGENT


def parse_owners_html(html_str: str) -> list[dict[str, str]]:
    """Parse ownership HTML table into list of owner dictionaries."""
    if not html_str:
        return []
    soup = BeautifulSoup(html_str, "html.parser")
    owners = []
    for row in soup.find_all("tr")[1:]:
        cols = row.find_all("td")
        if len(cols) >= 2:
            owners.append({"ime": cols[0].text.strip(), "udio": cols[1].text.strip()})
    return owners


def parse_parts_html(html_str: str) -> list[dict[str, str]]:
    """Parse land use parts HTML table into list of part dictionaries."""
    if not html_str:
        return []
    soup = BeautifulSoup(html_str, "html.parser")
    parts = []
    for row in soup.find_all("tr")[1:]:
        cols = row.find_all("td")
        if len(cols) >= 3:
            parts.append(
                {
                    "kultura": cols[0].text.strip() if len(cols) > 2 else "1",
                    "nacin_koriscenja": cols[1].text.strip(),
                    "povrsina": cols[2].text.strip(),
                }
            )
    return parts


def parse_date_html(html_str: str) -> str:
    """Extract replication date string from e-Katastar HTML snippet."""
    if not html_str:
        return ""
    soup = BeautifulSoup(html_str, "html.parser")
    text = soup.text
    date_match = re.search(r"(\d{2}\.\d{2}\.\d{4})", text)
    if date_match:
        return date_match.group(1)
    return text.replace("Датум ажурности података:", "").strip()


class CadastreRegistryClient:
    """
    Client for querying e-Katastar registry records.
    """

    def __init__(
        self,
        base_api_url: str = OWNER_API_BASE,
        city_id: str = DEFAULT_CITY_ID,
        city_name: str = DEFAULT_CITY_NAME,
        timeout: int = REQUEST_TIMEOUT,
        max_connections: int = 16,
    ):
        self.base_api_url = base_api_url.rstrip("/")
        self.city_id = str(city_id)
        self.city_name = city_name
        self.encoded_city = urllib.parse.quote(city_name)
        self.timeout = timeout

        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504], raise_on_status=False)
        adapter = HTTPAdapter(max_retries=retries, pool_connections=max_connections, pool_maxsize=max_connections)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update(
            {"User-Agent": USER_AGENT, "X-Requested-With": "XMLHttpRequest", "Referer": "https://ekatastar.rgurs.org/"}
        )

    def fetch_base_parcel_bundle(self, base_number: str) -> list[dict[str, Any]] | None:
        """
        Fetch all sub-parcels associated with a base parcel number.
        Returns list of parcel items from the registry API.
        """
        url = f"{self.base_api_url}/{self.city_id}/{self.encoded_city}/{base_number}"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    return data
        except (requests.RequestException, ValueError):
            return None
        return None

    def match_sub_parcel(self, parcel_items: list[dict[str, Any]], target_clean: str) -> dict[str, Any] | None:
        """
        Locate the specific sub-parcel record within a base parcel bundle.
        """
        for item in parcel_items:
            parcela_html = item.get("parcela", "")
            if not parcela_html:
                continue

            soup = BeautifulSoup(parcela_html, "html.parser")
            tds = soup.find_all("td")
            if tds:
                found_parcel = tds[0].text.strip().replace("-", "/").replace(" ", "")
                if found_parcel == target_clean:
                    return item
        return None
