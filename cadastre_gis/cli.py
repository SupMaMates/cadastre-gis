"""
Command Line Interface for CadastreGIS.
Provides rich CLI commands for analytics, web serving, CRS transformation,
scraping, and KML export.
"""

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cadastre_gis import __version__
from cadastre_gis.analytics.engine import CadastreAnalyticsEngine
from cadastre_gis.config import (
    DEFAULT_DATASET,
    DEFAULT_KO_ID,
    WEB_HOST,
    WEB_PORT,
)
from cadastre_gis.crs.kml import export_parcel_to_kml
from cadastre_gis.crs.transformer import reproject_geojson_collection

# Ensure UTF-8 output encoding across Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

console = Console(legacy_windows=False)


@click.group()
@click.version_option(version=__version__, prog_name="CadastreGIS")
def cli():
    """CadastreGIS: Advanced Cadastral & Land Registry Intelligence Platform."""


@cli.command("web")
@click.option("--host", default=WEB_HOST, help="Host interface to bind to.")
@click.option("--port", default=WEB_PORT, type=int, help="Port to listen on.")
@click.option("--debug", is_flag=True, help="Enable Flask debug mode.")
@click.option("--dataset", type=click.Path(exists=True), default=str(DEFAULT_DATASET), help="Path to GeoJSON dataset.")
def cmd_web(host, port, debug, dataset):
    """Launch the interactive Web GIS platform and REST API."""
    from cadastre_gis.web.app import create_app

    console.print(
        Panel(
            f"[bold green]Starting CadastreGIS Web Platform[/bold green]\n"
            f"URL: [link=http://{host}:{port}]http://{host}:{port}[/link]\n"
            f"Dataset: [cyan]{dataset}[/cyan]",
            title="CadastreGIS Server",
            border_style="blue",
        )
    )
    app = create_app(dataset_path=Path(dataset))
    app.run(host=host, port=port, debug=debug)


@cli.command("analyze")
@click.option("--dataset", type=click.Path(exists=True), default=str(DEFAULT_DATASET), help="Path to GeoJSON dataset.")
@click.option("--top", default=15, type=int, help="Number of items in leaderboards.")
@click.option("--export-dir", type=click.Path(), default=None, help="Directory to export CSVs and JSON report.")
@click.option("--no-entities", is_flag=True, help="Exclude institutional and legal entities from analysis.")
def cmd_analyze(dataset, top, export_dir, no_entities):
    """Run comprehensive econometric, inequality, and fragmentation analytics."""
    console.print(f"[bold blue]Analyzing cadastral dataset:[/bold blue] {dataset}")

    engine = CadastreAnalyticsEngine(Path(dataset))
    report = engine.generate_report(top_n=top, include_entities=not no_entities)
    m = report["metrics"]

    # 1. Inequality Panel
    inequality_table = Table(title="[bold yellow]Ekonometrija & Nejednakost Zemljišta[/bold yellow]", show_header=True)
    inequality_table.add_column("Metrika", style="cyan")
    inequality_table.add_column("Vrijednost", style="bold green", justify="right")

    inequality_table.add_row("Džini koeficijent (Gini)", f"{m['gini_coefficient']:.4f}")
    inequality_table.add_row("Theil indeks", f"{m['theil_index']:.4f}")
    inequality_table.add_row("Herfindahl-Hirschman (HHI)", f"{m['hhi_index']:.6f}")
    inequality_table.add_row("Palma omjer (Top 10% / Dno 40%)", f"{m['palma_ratio']:.2f}x")
    inequality_table.add_row("Top 1% vlasnika posjeduje", f"{m['top_1pct_share']:.2f}%")
    inequality_table.add_row("Top 5% vlasnika posjeduje", f"{m['top_5pct_share']:.2f}%")
    inequality_table.add_row("Top 10% vlasnika posjeduje", f"{m['top_10pct_share']:.2f}%")
    inequality_table.add_row("Top 20% vlasnika posjeduje", f"{m['top_20pct_share']:.2f}%")
    console.print(inequality_table)

    # 2. Key Volume KPIs
    console.print(
        Panel(
            f"Ukupno parcela: [bold]{m['total_parcels']:,}[/bold] | "
            f"Uknjiženi vlasnici: [bold]{m['unique_owners_count']:,}[/bold] | "
            f"Ukupna površina opštine: [bold]{m['total_cadastre_area_ha']:,} ha[/bold] ({m['total_cadastre_area_sqm']:,} m²)",
            title="[bold]Obim Katastarske Opštine[/bold]",
            border_style="green",
        )
    )

    # 3. Top Owners Table
    owners_table = Table(title=f"[bold]Top {top} Najvećih Posjednika Zemljišta[/bold]", show_header=True)
    owners_table.add_column("#", style="dim", justify="right")
    owners_table.add_column("Nosilac prava", style="bold")
    owners_table.add_column("Površina (m²)", justify="right")
    owners_table.add_column("Površina (ha)", justify="right", style="cyan")
    owners_table.add_column("Udio u opštini", justify="right", style="green")

    for i, (name, area) in enumerate(report["top_owners"].items(), 1):
        pct = (area / m["total_cadastre_area_sqm"]) * 100
        owners_table.add_row(str(i), name, f"{area:,.0f} m²", f"{(area / 10000):.2f} ha", f"{pct:.2f}%")
    console.print(owners_table)

    # 4. Top Clans / Surnames Table
    clans_table = Table(title=f"[bold]Moć Porodičnih Prezimena (Klanovi - Top {top})[/bold]", show_header=True)
    clans_table.add_column("Prezime", style="bold magenta")
    clans_table.add_column("Ukupan posjed loze (m²)", justify="right")
    clans_table.add_column("Površina (ha)", justify="right", style="cyan")

    for surname, area in report["clans"]["surname_wealth"].items():
        clans_table.add_row(surname, f"{area:,.0f} m²", f"{(area / 10000):.2f} ha")
    console.print(clans_table)

    # 5. Land Capability & Usage
    lu = report["land_use"]
    console.print(
        Panel(
            f"Ponderisana prosječna klasa zemljišta: [bold yellow]{lu.get('weighted_avg_class', 'N/A')}[/bold yellow]\n"
            f"Kategorije: {json.dumps(lu.get('category_shares_pct', {}), ensure_ascii=False, indent=2)}",
            title="[bold]Poljoprivredna Bonitetna Struktura[/bold]",
            border_style="yellow",
        )
    )

    # Export if requested
    if export_dir:
        engine.export_csvs(export_dir)
        report_path = Path(export_dir) / "analytics_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        console.print(f"[bold green]Report & CSVs exported successfully to:[/bold green] {export_dir}")


@cli.command("transform")
@click.argument("input_file", type=click.Path(exists=True))
@click.argument("output_file", type=click.Path())
@click.option("--from-epsg", default=31276, type=int, help="Source EPSG code (e.g. 31276 for MGI Zone 6).")
@click.option("--to-epsg", default=4326, type=int, help="Target EPSG code (e.g. 4326 for WGS84).")
@click.option("--precision", default=6, type=int, help="Coordinate decimal rounding.")
def cmd_transform(input_file, output_file, from_epsg, to_epsg, precision):
    """Transform GeoJSON from Balkan Gauss-Kruger to WGS84 with Helmert shift."""
    console.print(f"Reprojecting [cyan]{input_file}[/cyan] from EPSG:{from_epsg} to EPSG:{to_epsg}...")
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    reprojected = reproject_geojson_collection(data, source_epsg=from_epsg, target_epsg=to_epsg, precision=precision)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(reprojected, f, ensure_ascii=False)

    console.print(f"[bold green]Success![/bold green] Saved reprojected GeoJSON to [cyan]{output_file}[/cyan]")


@cli.command("kml")
@click.argument("parcel_id")
@click.option("--dataset", type=click.Path(exists=True), default=str(DEFAULT_DATASET), help="Path to GeoJSON dataset.")
@click.option("--output", type=click.Path(), default=None, help="Output KML file path.")
def cmd_kml(parcel_id, dataset, output):
    """Export a specific parcel to styled Google Earth KML format."""
    with open(dataset, "r", encoding="utf-8") as f:
        data = json.load(f)

    clean_target = parcel_id.strip()
    found = None
    for feat in data.get("features", []):
        p = feat.get("properties", {})
        if str(p.get("parcel_id")) == clean_target or str(p.get("broj")) == clean_target:
            found = feat
            break

    if not found:
        console.print(f"[bold red]Error:[/bold red] Parcel {parcel_id} not found in {dataset}")
        sys.exit(1)

    kml_text = export_parcel_to_kml(found)
    out_path = output or f"parcel_{clean_target.replace('/', '_')}.kml"

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(kml_text)

    console.print(f"[bold green]Generated KML:[/bold green] {out_path}")


@cli.command("info")
@click.option("--dataset", type=click.Path(exists=True), default=str(DEFAULT_DATASET), help="Path to GeoJSON dataset.")
def cmd_info(dataset):
    """Display system metadata, CRS configuration, and dataset statistics."""
    with open(dataset, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data.get("metadata", {})
    features = data.get("features", [])

    console.print(
        Panel(
            f"[bold]CadastreGIS Platform v{__version__}[/bold]\n"
            f"Municipality: [bold green]{meta.get('municipality', 'Donji Žabar')}[/bold green] (KO: {meta.get('ko_id', DEFAULT_KO_ID)})\n"
            f"Parcels Count: [bold]{len(features):,}[/bold]\n"
            f"CRS: [cyan]EPSG:4326 (WGS84)[/cyan] - RFC 7946 compliant\n"
            f"Original Source CRS: [cyan]{meta.get('source_crs', 'EPSG:31276')}[/cyan]\n"
            f"Default Dataset Path: {dataset}",
            title="System & Dataset Information",
            border_style="blue",
        )
    )


def main():
    cli()


if __name__ == "__main__":
    main()
