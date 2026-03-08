"""
cli.py – Command-line interface for the Dental Lead System.

Usage:
  python cli.py discover
  python cli.py enrich
  python cli.py profile
  python cli.py score
  python cli.py export
  python cli.py full-run
  python cli.py stats
"""
import logging
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.logging import RichHandler

import config

# Setup logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format="%(message)s",
    handlers=[
        RichHandler(rich_tracebacks=True),
        logging.FileHandler(config.LOGS_DIR / "dental_leads.log"),
    ],
)
logger = logging.getLogger(__name__)
console = Console()

app = typer.Typer(
    name="dental-leads",
    help="🦷 Dental Lead Generation System – DACH Premium Dentistry",
    add_completion=False,
)


@app.command()
def discover(
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Custom search query"),
    limit: int = typer.Option(10, "--limit", "-l", help="Max results per query"),
):
    """Discover new dental practice leads via web search."""
    from pipeline import run_discover
    queries = [query] if query else None
    with console.status("[bold green]Discovering leads..."):
        count = run_discover(queries=queries, max_per_query=limit)
    console.print(f"[green]✓ {count} new leads discovered[/green]")


@app.command()
def enrich(
    limit: int = typer.Option(50, "--limit", "-l", help="Max leads to enrich"),
):
    """Crawl and extract data from discovered leads."""
    from pipeline import run_enrich
    with console.status("[bold green]Enriching leads..."):
        count = run_enrich(limit=limit)
    console.print(f"[green]✓ {count} leads enriched[/green]")


@app.command()
def profile(
    limit: int = typer.Option(50, "--limit", "-l", help="Max leads to profile"),
):
    """AI-profile enriched leads."""
    from pipeline import run_profile
    with console.status("[bold green]Profiling leads with AI..."):
        count = run_profile(limit=limit)
    console.print(f"[green]✓ {count} leads profiled[/green]")


@app.command()
def score(
    limit: int = typer.Option(200, "--limit", "-l", help="Max leads to score"),
):
    """Score and tier all profiled leads."""
    from pipeline import run_score
    with console.status("[bold green]Scoring leads..."):
        count = run_score(limit=limit)
    console.print(f"[green]✓ {count} leads scored[/green]")


@app.command()
def export():
    """Export leads to CSV files."""
    from pipeline import run_export
    with console.status("[bold green]Exporting to CSV..."):
        result = run_export()
    console.print(f"[green]✓ Exported:[/green] all={result['all']}, top={result['top']}, review={result['review']}")
    console.print(f"[dim]Files in: {config.EXPORTS_DIR}[/dim]")


@app.command(name="full-run")
def full_run(
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Custom query"),
):
    """Run the complete pipeline: discover → enrich → profile → score → export."""
    from pipeline import run_full
    queries = [query] if query else None
    console.print("[bold cyan]🦷 Starting Full Pipeline Run...[/bold cyan]")
    result = run_full(queries=queries)
    console.print(f"\n[bold green]✅ Pipeline Complete[/bold green]")
    for k, v in result.items():
        console.print(f"  {k}: {v}")


@app.command()
def stats():
    """Show database statistics and top leads."""
    from db import get_db
    db = get_db()

    total = db["companies"].count
    by_status = {}
    for row in db.execute("SELECT status, COUNT(*) as n FROM companies GROUP BY status"):
        by_status[row[0]] = row[1]

    console.print(f"\n[bold]📊 Database Stats[/bold]")
    console.print(f"Total companies: {total}")
    for status, count in by_status.items():
        console.print(f"  {status}: {count}")

    # Top leads table
    top = list(db["companies"].rows_where(
        "total_score >= ?", [config.SCORE_THRESHOLD_TOP],
        order_by="total_score desc",
        limit=20,
    ))

    if top:
        table = Table(title=f"\n🏆 Top Leads (score >= {config.SCORE_THRESHOLD_TOP})")
        table.add_column("Score", style="bold green", width=7)
        table.add_column("Tier", width=8)
        table.add_column("Domain", width=30)
        table.add_column("Name", width=30)
        table.add_column("Positioning", width=12)
        table.add_column("City", width=15)
        for c in top:
            table.add_row(
                str(c.get("total_score", "")),
                c.get("score_tier", ""),
                c.get("domain", ""),
                c.get("practice_name", "")[:30],
                c.get("positioning", ""),
                c.get("city", ""),
            )
        console.print(table)
    else:
        console.print("[yellow]No scored leads yet. Run: python cli.py full-run[/yellow]")


@app.command()
def reset():
    """⚠️  Delete the database and start fresh."""
    confirm = typer.confirm("This will DELETE all data. Are you sure?")
    if confirm:
        config.DB_PATH.unlink(missing_ok=True)
        console.print("[red]Database deleted.[/red]")
    else:
        console.print("Aborted.")


if __name__ == "__main__":
    app()
