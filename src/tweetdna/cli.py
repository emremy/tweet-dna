"""TweetDNA CLI using typer."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import typer
from rich.console import Console
from rich.table import Table

from tweetdna.config import get_config
from tweetdna.importer import ExtensionImporter
from tweetdna.providers.factory import get_provider
from tweetdna.schemas import SpiceLevel
from tweetdna.services import GeneratorService, ProfilerService, ReviewerService
from tweetdna.storage import Database, Repository

app = typer.Typer(
    name="tweetdna",
    help="Local-first Twitter persona profiling and tweet generation.",
    no_args_is_help=True,
)
generate_app = typer.Typer(help="Generate tweets or threads.")
import_app = typer.Typer(help="Import data from external sources.")
app.add_typer(generate_app, name="generate")
app.add_typer(import_app, name="import")

console = Console()


def get_db_and_repo() -> Tuple[Database, Repository]:
    """Initialize database and repository."""
    config = get_config()
    db = Database(config.db_path)
    db.connect()
    db.initialize()
    return db, Repository(db)


@import_app.command("extension")
def import_extension(
    path: Path = typer.Option(..., "--path", "-p", help="Path to extension export file (JSONL or JSON)"),
    validate_only: bool = typer.Option(False, "--validate", help="Validate file without importing"),
) -> None:
    """Import tweets from browser extension export."""
    db, repo = get_db_and_repo()

    try:
        importer = ExtensionImporter(repository=repo)
        
        if validate_only:
            is_valid, message = importer.validate_file(path)
            if is_valid:
                console.print(f"[green]{message}[/green]")
            else:
                console.print(f"[red]{message}[/red]")
                raise typer.Exit(1)
            return
        
        with console.status(f"[bold green]Importing from {path}..."):
            imported, skipped, deduped = importer.import_file(path)

        console.print(f"[green]Import complete.[/green]")
        console.print(f"  Imported: {imported}")
        console.print(f"  Skipped (invalid): {skipped}")
        console.print(f"  Skipped (duplicate): {deduped}")
        
        total = repo.get_tweet_count()
        console.print(f"\nTotal tweets in database: {total}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    finally:
        db.close()


@app.command()
def profile(
    sample: int = typer.Option(300, "--sample", help="Number of tweets to sample for profiling"),
    force: bool = typer.Option(False, "--force", help="Force rebuild even if persona exists"),
    persona_name: Optional[str] = typer.Option(None, "--persona-name", help="Optional label"),
) -> None:
    """Build or refresh persona JSON from stored tweets."""
    config = get_config()
    db, repo = get_db_and_repo()

    try:
        provider = get_provider(config, role="profile")
        profiler = ProfilerService(repository=repo, provider=provider)

        with console.status("[bold green]Building persona..."):
            persona = profiler.build_persona(
                sample_size=sample,
                force=force,
            )

        if persona_name:
            persona.display_name = persona_name

        console.print(f"[green]Persona v{persona.version} created successfully.[/green]")
        console.print(f"Display name: {persona.display_name}")
        console.print(f"Topics: {', '.join(t.name for t in persona.topics)}")
        console.print(f"Voice: {persona.voice_rules.directness} directness, {persona.voice_rules.sentence_length} sentences")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    finally:
        db.close()


@generate_app.command("tweet")
def generate_tweet(
    topic: str = typer.Option(..., "--topic", help="Topic or prompt for generation"),
    n: int = typer.Option(5, "--n", help="Number of drafts to generate"),
    spice: str = typer.Option("medium", "--spice", help="Spice level: low, medium, high"),
    use_examples: bool = typer.Option(False, "--use-examples", help="Include similar historical tweets"),
    min_chars: int = typer.Option(0, "--min-chars", help="Minimum characters per tweet (0 = no minimum)"),
    max_chars: int = typer.Option(280, "--max-chars", help="Maximum characters per tweet"),
) -> None:
    """Generate tweet drafts."""
    config = get_config()
    db, repo = get_db_and_repo()

    try:
        provider = get_provider(config, role="generate")
        generator = GeneratorService(repository=repo, provider=provider)

        with console.status(f"[bold green]Generating {n} tweet drafts..."):
            drafts = generator.generate_tweets(
                topic=topic,
                n=n,
                spice=spice,  # type: ignore
                min_chars=min_chars,
                max_chars=max_chars,
                use_examples=use_examples,
            )

        if drafts:
            console.print(f"[green]Generated {len(drafts)} drafts:[/green]\n")
            for i, draft in enumerate(drafts, 1):
                console.print(f"[bold]Draft {i}:[/bold]")
                console.print(f"  {draft.text}")
                console.print(f"  [dim]Tags: {', '.join(draft.tags)}[/dim]")
                console.print(f"  [dim]Confidence: {draft.confidence:.0%}[/dim]")
                console.print()
        else:
            console.print("[yellow]No drafts generated.[/yellow]")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    finally:
        db.close()


@generate_app.command("thread")
def generate_thread(
    topic: str = typer.Option(..., "--topic", help="Thread topic"),
    tweets: int = typer.Option(5, "--tweets", help="Number of tweets in thread"),
    spice: str = typer.Option("medium", "--spice", help="Spice level: low, medium, high"),
    draft: bool = typer.Option(False, "--draft", help="Generate full drafts (otherwise outline)"),
    min_chars: int = typer.Option(0, "--min-chars", help="Minimum characters per tweet (0 = no minimum)"),
    max_chars: int = typer.Option(280, "--max-chars", help="Maximum characters per tweet"),
) -> None:
    """Generate a thread outline or full thread drafts."""
    config = get_config()
    db, repo = get_db_and_repo()

    try:
        provider = get_provider(config, role="generate")
        generator = GeneratorService(repository=repo, provider=provider)

        mode = "full drafts" if draft else "outline"
        with console.status(f"[bold green]Generating thread {mode}..."):
            thread_drafts = generator.generate_thread(
                topic=topic,
                tweet_count=tweets,
                spice=spice,  # type: ignore
                full_draft=draft,
                min_chars=min_chars,
                max_chars=max_chars,
            )

        if thread_drafts:
            console.print(f"[green]Generated {len(thread_drafts)}-part thread:[/green]\n")
            for i, item in enumerate(thread_drafts, 1):
                console.print(f"[bold]{i}/{len(thread_drafts)}:[/bold]")
                console.print(f"  {item.text}")
                console.print()
        else:
            console.print("[yellow]No thread generated.[/yellow]")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    finally:
        db.close()


# Valid reply tones for CLI help
REPLY_TONES = [
    "neutral", "supportive", "curious", "playful", "sarcastic",
    "critical", "angry", "excited", "thoughtful"
]


@generate_app.command("reply")
def generate_reply(
    to: str = typer.Option(..., "--to", "-t", help="The tweet text you're replying to"),
    tone: str = typer.Option("neutral", "--tone", help=f"Reply tone: {', '.join(REPLY_TONES)}"),
    n: int = typer.Option(3, "--n", help="Number of reply drafts to generate"),
    min_chars: int = typer.Option(0, "--min-chars", help="Minimum characters (0 = no minimum)"),
    max_chars: int = typer.Option(280, "--max-chars", help="Maximum characters"),
    context: Optional[str] = typer.Option(None, "--context", "-c", help="Additional context (who posted, thread info)"),
) -> None:
    """Generate reply drafts to an existing tweet."""
    # Validate tone
    if tone not in REPLY_TONES:
        console.print(f"[red]Invalid tone '{tone}'. Choose from: {', '.join(REPLY_TONES)}[/red]")
        raise typer.Exit(1)

    config = get_config()
    db, repo = get_db_and_repo()

    try:
        provider = get_provider(config, role="generate")
        generator = GeneratorService(repository=repo, provider=provider)

        with console.status(f"[bold green]Generating {n} {tone} replies..."):
            drafts = generator.generate_replies(
                original_tweet=to,
                tone=tone,  # type: ignore
                n=n,
                min_chars=min_chars,
                max_chars=max_chars,
                context=context,
            )

        if drafts:
            console.print(f"\n[dim]Replying to:[/dim] \"{to[:100]}{'...' if len(to) > 100 else ''}\"")
            console.print(f"[dim]Tone:[/dim] {tone}\n")
            console.print(f"[green]Generated {len(drafts)} reply drafts:[/green]\n")
            
            for i, draft in enumerate(drafts, 1):
                console.print(f"[bold]Reply {i}:[/bold]")
                console.print(f"  {draft.text}")
                console.print(f"  [dim]Approach: {draft.tags[0] if draft.tags else 'N/A'}[/dim]")
                console.print(f"  [dim]Confidence: {draft.confidence:.0%}[/dim]")
                console.print()
        else:
            console.print("[yellow]No replies generated.[/yellow]")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    finally:
        db.close()


@app.command()
def review(
    last: int = typer.Option(5, "--last", "-n", help="Review last N drafts"),
    all_drafts: bool = typer.Option(False, "--all", "-a", help="Review all unreviewed drafts"),
    auto_refine: bool = typer.Option(False, "--auto-refine", help="Auto-generate refined versions"),
) -> None:
    """Review drafts for persona alignment."""
    config = get_config()
    db, repo = get_db_and_repo()

    try:
        provider = get_provider(config, role="review")
        reviewer = ReviewerService(repository=repo, provider=provider)

        # Determine how many to fetch
        limit = 1000 if all_drafts else last

        with console.status(f"[bold green]Reviewing drafts..."):
            results = reviewer.review_drafts(last_n=limit, auto_refine=auto_refine)

        if results:
            console.print(f"[green]Reviewed {len(results)} draft(s):[/green]\n")
            
            table = Table(title="Review Results")
            table.add_column("Draft ID", style="dim")
            table.add_column("Score", justify="right")
            table.add_column("Violations")
            table.add_column("Revised", justify="center")

            for r in results:
                score_color = "green" if r.alignment_score >= 80 else "yellow" if r.alignment_score >= 60 else "red"
                violations = ", ".join(r.violations[:2]) if r.violations else "-"
                revised = "Yes" if r.revised_text else "-"
                
                table.add_row(
                    str(r.draft_id)[:8],
                    f"[{score_color}]{r.alignment_score:.0f}[/{score_color}]",
                    violations,
                    revised,
                )

            console.print(table)
        else:
            console.print("[yellow]No drafts to review. Generate some first.[/yellow]")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    finally:
        db.close()


@app.command("api")
def run_api(
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind to"),
    port: int = typer.Option(8765, "--port", help="Port to bind to"),
) -> None:
    """Run the local FastAPI server."""
    import uvicorn
    
    console.print(f"[green]Starting TweetDNA API at http://{host}:{port}[/green]")
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    
    uvicorn.run(
        "tweetdna.api.main:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    app()
