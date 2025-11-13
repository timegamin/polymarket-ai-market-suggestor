from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table

from .config import get_settings
from .orchestrator import run_pipeline
from .reporting import bundle_to_markdown, bundle_to_summary_row
from .storage import BundleStore
from .analytics import generate_insights

app = typer.Typer(help="PolySuggest AI – Polymarket AI market suggester")
console = Console()


@app.command()
def suggest(
    topic: str = typer.Argument(..., help="High-level topic or question to explore"),
    keywords: Optional[str] = typer.Option(
        None,
        help="Comma-separated keywords to bias trend scanning (default: uses config)",
    ),
    count: int = typer.Option(3, "--count", "-c", help="Number of market suggestions to generate"),
    include_trending: bool = typer.Option(
        True,
        "--include-trending/--no-trending",
        help="Include Polymarket trending markets in overlap detection",
    ),
    include_crypto: bool = typer.Option(
        True,
        "--include-crypto/--no-crypto",
        help="Include CoinGecko trending assets as additional signals",
    ),
    save: bool = typer.Option(
        True,
        "--save/--no-save",
        help="Persist results to the local PolySuggest bundle store",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Optional path to save JSON bundle",
    ),
    markdown: Optional[Path] = typer.Option(
        None,
        "--markdown",
        "-m",
        help="Optional path to save Markdown report",
    ),
) -> None:
    """
    Generate new Polymarket-ready market suggestions powered by AI.
    """

    settings = get_settings()
    if not settings.openai_api_key:
        typer.secho(
            "OPENAI_API_KEY not set. Fallback generator will be used instead of GPT.",
            fg=typer.colors.YELLOW,
        )

    keyword_list = [kw.strip() for kw in keywords.split(",")] if keywords else None

    logger.info("Running suggestion pipeline topic=%s keywords=%s", topic, keyword_list)
    bundle = run_pipeline(
        topic=topic,
        keywords=keyword_list,
        suggestion_count=count,
        include_trending=include_trending,
        include_crypto=include_crypto,
    )

    table = Table(title=f"PolySuggest AI — {topic}")
    table.add_column("Title", style="bold cyan")
    table.add_column("Confidence", justify="right")
    table.add_column("Resolution Source", style="magenta")
    table.add_column("Tags", style="green")

    for suggestion in bundle.suggestions:
        table.add_row(
            suggestion.title,
            f"{suggestion.confidence:.2f}",
            suggestion.resolution_source,
            ", ".join(suggestion.tags),
        )

    console.print(table)

    console.print("\n[bold]Rationales[/bold]")
    for suggestion in bundle.suggestions:
        console.print(f"[cyan]{suggestion.title}[/cyan]: {suggestion.rationale}")

    if output:
        output.write_text(bundle.model_dump_json(indent=2))
        console.print(f"\n[green]Saved JSON report to[/green] {output}")

    if markdown:
        markdown.write_text(bundle_to_markdown(bundle))
        console.print(f"[green]Saved Markdown report to[/green] {markdown}")

    if save:
        store = BundleStore()
        run_id = store.persist(bundle)
        console.print(f"[green]Saved bundle to storage as run #{run_id} ({store.db_path})[/green]")


@app.command()
def summarize(
    history: Optional[Path] = typer.Argument(
        None, help="Optional path containing JSON bundles; if omitted uses local storage"
    ),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum number of runs to display"),
) -> None:
    """
    Summarize historic suggestion bundles (JSON) into a table view.
    """
    if history:
        rows = []
        for json_file in sorted(history.glob("*.json")):
            try:
                data = json.loads(json_file.read_text())
                rows.append(bundle_to_summary_row(json_file.stem, data))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping %s: %s", json_file, exc)
        if not rows:
            typer.secho("No valid JSON bundles found.", fg=typer.colors.YELLOW)
            raise typer.Exit(code=1)
        table = Table(title="PolySuggest History (filesystem)")
        table.add_column("File", style="bold")
        table.add_column("Topic")
        table.add_column("Generated")
        table.add_column("Top Suggestion")
        table.add_column("Confidence")
        table.add_column("Tags")
        for row in rows:
            table.add_row(*row)
        console.print(table)
    else:
        store = BundleStore()
        runs = store.history(limit=limit)
        if not runs:
            typer.secho("No stored runs found.", fg=typer.colors.YELLOW)
            raise typer.Exit(code=1)
        table = Table(title="PolySuggest History (storage)")
        table.add_column("Run ID", style="bold")
        table.add_column("Topic")
        table.add_column("Generated")
        table.add_column("Top Suggestion")
        table.add_column("Confidence")
        table.add_column("Tags")
        for run in runs:
            table.add_row(
                str(run.run_id),
                run.topic,
                run.generated_at.strftime("%Y-%m-%d %H:%M"),
                run.top_title,
                f"{run.top_confidence:.2f}",
                ", ".join(run.tags),
            )
        console.print(table)


@app.command()
def show(run_id: int = typer.Argument(..., help="Run ID from storage to display")) -> None:
    """
    Display full details for a stored suggestion bundle.
    """
    store = BundleStore()
    try:
        run = store.get(run_id)
    except KeyError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)

    bundle = run.to_bundle()
    console.print(f"[bold]Run #{run.run_id}[/bold] — {bundle.topic} ({run.generated_at})")
    console.print(f"Keywords: {', '.join(bundle.keywords) or 'auto'}")
    console.print(f"Average confidence: {run.avg_confidence:.2f} (top {run.top_confidence:.2f})")
    console.print("\n[bold]Suggestions[/bold]")
    for suggestion in bundle.suggestions:
        console.print(f"\n[cyan]{suggestion.title}[/cyan] — {suggestion.confidence:.2f}")
        console.print(f"Tags: {', '.join(suggestion.tags)}")
        console.print(f"Resolution: {suggestion.resolution_source}")
        console.print(f"Yes: {suggestion.yes_outcome}")
        console.print(f"No: {suggestion.no_outcome}")
        console.print(f"Rationale: {suggestion.rationale}")
        if suggestion.references:
            console.print(f"References: {', '.join(str(ref) for ref in suggestion.references)}")


@app.command()
def insights(limit: int = typer.Option(None, "--limit", "-l", help="Number of runs to consider")) -> None:
    """
    Generate aggregate analytics from stored runs.
    """
    store = BundleStore()
    runs = store.history(limit=limit)
    summary = generate_insights(runs)
    if summary["total_runs"] == 0:
        typer.secho("No data available. Generate suggestions with --save first.", fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)

    console.print("[bold]PolySuggest Storage Insights[/bold]")
    console.print(f"Total runs: {summary['total_runs']}")
    console.print(f"Unique topics: {summary['unique_topics']}")
    console.print(f"Average confidence: {summary['avg_confidence']:.2f}")
    console.print(f"Average sentiment: {summary['avg_sentiment']:.2f}")

    if summary["top_tags"]:
        console.print("\nTop tags:")
        for tag, count in summary["top_tags"]:
            console.print(f"- {tag}: {count}")
    if summary["top_topics"]:
        console.print("\nMost frequent topics:")
        for topic, count in summary["top_topics"]:
            console.print(f"- {topic}: {count}")


if __name__ == "__main__":
    app()


