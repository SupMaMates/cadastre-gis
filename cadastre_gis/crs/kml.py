"""
KML Exporter for Cadastral Parcels.
Generates compliant, styled KML 2.2 documents for Google Earth, GIS desktop suites, and mobile GPS apps.
"""

import html
from typing import Any


def _coords_to_kml_linear_ring(coordinates: list[list[float]]) -> str:
    """Format coordinate list as KML <coordinates>lon,lat,alt lon,lat,alt ...</coordinates>"""
    return " ".join(f"{pt[0]},{pt[1]},0" for pt in coordinates)


def _format_parcel_html_description(props: dict[str, Any]) -> str:
    """Generate clean HTML popup description for Google Earth."""
    parcel_id = html.escape(str(props.get("parcel_id") or props.get("BROJ") or "N/A"))
    area_sqm = props.get("area_sqm") or props.get("POVRSINA") or 0
    pl_broj = html.escape(str(props.get("pl_broj") or props.get("PL_BROJ") or "N/A"))
    municipality = html.escape(str(props.get("ko_naziv") or props.get("KO_NAZIV") or "Donji Žabar"))

    owners_html = ""
    owners = props.get("owners", []) or props.get("REGISTRY_OWNERS", [])
    if owners:
        owners_html = "<h4>Vlasnici / Posjednici</h4><table border='1' cellpadding='4' cellspacing='0' style='border-collapse:collapse;font-size:12px;width:100%;'>"
        owners_html += "<tr style='background:#f0f0f0;'><th>Ime i prezime</th><th>Udio</th></tr>"
        for o in owners:
            name = html.escape(str(o.get("name") or o.get("ime") or ""))
            share = html.escape(str(o.get("share_raw") or o.get("udio") or "1/1"))
            owners_html += f"<tr><td>{name}</td><td>{share}</td></tr>"
        owners_html += "</table>"

    parts_html = ""
    parts = props.get("parts", []) or props.get("REGISTRY_PARTS", [])
    if parts:
        parts_html = "<h4>Dijelovi parcele</h4><table border='1' cellpadding='4' cellspacing='0' style='border-collapse:collapse;font-size:12px;width:100%;'>"
        parts_html += "<tr style='background:#f0f0f0;'><th>Način korišćenja</th><th>Površina</th></tr>"
        for p in parts:
            ut = html.escape(str(p.get("usage_type") or p.get("nacin_koriscenja") or ""))
            pt_a = html.escape(str(p.get("area_sqm") or p.get("povrsina") or ""))
            parts_html += f"<tr><td>{ut}</td><td>{pt_a} m²</td></tr>"
        parts_html += "</table>"

    return f"""<![CDATA[
    <div style="font-family:Arial,sans-serif;font-size:13px;max-width:320px;">
        <h3 style="color:#1e3a8a;margin-top:0;">Parcela {parcel_id}</h3>
        <p><b>Opština:</b> {municipality}<br/>
        <b>Broj lista nepokretnosti:</b> {pl_broj}<br/>
        <b>Površina:</b> {area_sqm:,.0f} m² ({(area_sqm / 10000):.4f} ha)</p>
        {owners_html}
        {parts_html}
    </div>
    ]]>"""


def export_parcel_to_kml(
    feature: dict[str, Any],
    document_name: str | None = None,
    line_color: str = "ff2563eb",  # AABBCCDD format: opacity, blue, green, red
    fill_color: str = "4d2563eb",
    line_width: float = 2.5,
) -> str:
    """
    Generate styled KML for a single parcel GeoJSON feature (coordinates in WGS84).
    """
    props = feature.get("properties", {})
    parcel_id = str(props.get("parcel_id") or props.get("BROJ") or "Parcel")
    doc_title = document_name or f"Parcel {parcel_id} - Donji Zabar"

    geom = feature.get("geometry", {})
    geom_type = geom.get("type", "")
    coordinates = geom.get("coordinates", [])

    polygons_kml = []
    if geom_type == "Polygon":
        outer_ring = _coords_to_kml_linear_ring(coordinates[0])
        inner_rings = "".join(
            f"<innerBoundaryIs><LinearRing><coordinates>{_coords_to_kml_linear_ring(ring)}</coordinates></LinearRing></innerBoundaryIs>"
            for ring in coordinates[1:]
        )
        polygons_kml.append(f"""
        <Polygon>
            <outerBoundaryIs><LinearRing><coordinates>{outer_ring}</coordinates></LinearRing></outerBoundaryIs>
            {inner_rings}
        </Polygon>
        """)
    elif geom_type == "MultiPolygon":
        for poly_coords in coordinates:
            outer_ring = _coords_to_kml_linear_ring(poly_coords[0])
            inner_rings = "".join(
                f"<innerBoundaryIs><LinearRing><coordinates>{_coords_to_kml_linear_ring(ring)}</coordinates></LinearRing></innerBoundaryIs>"
                for ring in poly_coords[1:]
            )
            polygons_kml.append(f"""
            <Polygon>
                <outerBoundaryIs><LinearRing><coordinates>{outer_ring}</coordinates></LinearRing></outerBoundaryIs>
                {inner_rings}
            </Polygon>
            """)

    polys_body = "\n".join(polygons_kml)
    desc_cdata = _format_parcel_html_description(props)

    kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{html.escape(doc_title)}</name>
    <Style id="parcelStyle">
      <LineStyle>
        <color>{line_color}</color>
        <width>{line_width}</width>
      </LineStyle>
      <PolyStyle>
        <color>{fill_color}</color>
      </PolyStyle>
    </Style>
    <Placemark>
      <name>Parcela {html.escape(parcel_id)}</name>
      <styleUrl>#parcelStyle</styleUrl>
      <description>{desc_cdata}</description>
      <MultiGeometry>
        {polys_body}
      </MultiGeometry>
    </Placemark>
  </Document>
</kml>"""
    return kml.strip()


def export_features_to_kml(features: list[dict[str, Any]], title: str = "Cadastral Parcels") -> str:
    """Generate styled KML for a list of parcel features."""
    placemarks = []
    for feat in features:
        props = feat.get("properties", {})
        parcel_id = str(props.get("parcel_id") or props.get("BROJ") or "Parcel")
        geom = feat.get("geometry", {})
        coords = geom.get("coordinates", [])
        geom_type = geom.get("type", "")

        if geom_type == "Polygon" and coords:
            ring = _coords_to_kml_linear_ring(coords[0])
            placemark = f"""
            <Placemark>
              <name>Parcela {html.escape(parcel_id)}</name>
              <styleUrl>#parcelStyle</styleUrl>
              <description>{_format_parcel_html_description(props)}</description>
              <Polygon>
                <outerBoundaryIs><LinearRing><coordinates>{ring}</coordinates></LinearRing></outerBoundaryIs>
              </Polygon>
            </Placemark>
            """
            placemarks.append(placemark)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{html.escape(title)}</name>
    <Style id="parcelStyle">
      <LineStyle>
        <color>ff2563eb</color>
        <width>2</width>
      </LineStyle>
      <PolyStyle>
        <color>332563eb</color>
      </PolyStyle>
    </Style>
    {"".join(placemarks)}
  </Document>
</kml>""".strip()
