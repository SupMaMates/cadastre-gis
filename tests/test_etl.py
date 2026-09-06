"""
Unit tests for ETL HTML parsing and sub-parcel matching.
"""

from cadastre_gis.etl.rgurs_client import CadastreRegistryClient, parse_date_html, parse_owners_html, parse_parts_html


def test_parse_owners_html():
    """Test extracting owners and shares from HTML table."""
    html_sample = """
    <table class='ui mini very compact table'>
      <thead><tr><th>Naziv</th><th>Udio prava</th></tr></thead>
      <tbody>
        <tr><td>Мутавчић (Живана) Ратко</td><td>1/1</td></tr>
        <tr><td>Ђокановић (Славка) Младен</td><td>1/2</td></tr>
      </tbody>
    </table>
    """
    owners = parse_owners_html(html_sample)
    assert len(owners) == 2
    assert owners[0]["ime"] == "Мутавчић (Живана) Ратко"
    assert owners[0]["udio"] == "1/1"
    assert owners[1]["ime"] == "Ђокановић (Славка) Младен"
    assert owners[1]["udio"] == "1/2"


def test_parse_parts_html():
    """Test extracting land use parts and areas from HTML table."""
    html_sample = """
    <table>
      <thead><tr><th>Broj</th><th>Način korišćenja</th><th>Površina</th></tr></thead>
      <tr><td>1</td><td>Стамбени објекат</td><td>103 м2</td></tr>
      <tr><td>1</td><td>Двориште</td><td>914 м2</td></tr>
      <tr><td>1</td><td>Њива 3. класе</td><td>5000 м2</td></tr>
    </table>
    """
    parts = parse_parts_html(html_sample)
    assert len(parts) == 3
    assert parts[0]["nacin_koriscenja"] == "Стамбени објекат"
    assert parts[0]["povrsina"] == "103 м2"
    assert parts[1]["nacin_koriscenja"] == "Двориште"
    assert parts[2]["nacin_koriscenja"] == "Њива 3. класе"


def test_parse_date_html():
    """Test parsing data replication date."""
    html_sample = "<div class='ui blue segment'>Датум ажурности података: <b>18.04.2026</b></div>"
    date_str = parse_date_html(html_sample)
    assert date_str == "18.04.2026"


def test_match_sub_parcel():
    """Test matching sub-parcel in multi-parcel array."""
    client = CadastreRegistryClient()
    mock_bundle = [
        {
            "parcela": "<table><tr><td>1376/1</td><td>100</td></tr></table>",
            "posjed_vlasnistvo": "<table><tr><td>Vlasnik 1</td><td>1/1</td></tr></table>",
        },
        {
            "parcela": "<table><tr><td>1376/2</td><td>200</td></tr></table>",
            "posjed_vlasnistvo": "<table><tr><td>Vlasnik 2</td><td>1/1</td></tr></table>",
        },
    ]

    matched = client.match_sub_parcel(mock_bundle, "1376/2")
    assert matched is not None
    assert "1376/2" in matched["parcela"]

    not_matched = client.match_sub_parcel(mock_bundle, "1376/99")
    assert not_matched is None
