"""Main CLI application for Fantasy WAR calculator."""

from pathlib import Path
from typing import List, Optional
import json
import csv
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint
from loguru import logger

from fantasy_war.config.settings import settings
from fantasy_war.config.leagues import LeagueConfig, fal_league
from fantasy_war.config.scoring import Position
from fantasy_war.data.loaders import NFLDataLoader
from fantasy_war.data.processors import StatsProcessor
from fantasy_war.calculators.war_engine import WARCalculator
from fantasy_war.calculators.auction_values import AuctionValueCalculator
from fantasy_war.data.cache import cache_manager

# Initialize Typer app and console
app = typer.Typer(
    name="fantasy-war",
    help="Fantasy Football WAR (Wins Above Replacement) Calculator with MPPR scoring",
    add_completion=False,
    rich_markup_mode="rich"
)
console = Console()


@app.callback()
def main(
    debug: bool = typer.Option(
        False, 
        "--debug", 
        help="Enable debug logging"
    ),
    cache_enabled: bool = typer.Option(
        True, 
        "--cache/--no-cache", 
        help="Enable/disable caching"
    ),
):
    """Fantasy Football WAR Calculator - Dominate your league with advanced analytics."""
    # Configure logging
    log_level = "DEBUG" if debug else settings.logging.level
    logger.remove()
    logger.add(
        lambda msg: console.print(msg, end=""),
        level=log_level,
        format="{level}: {message}"
    )
    
    # Update cache settings
    settings.cache.enabled = cache_enabled
    
    if debug:
        logger.info(f"Debug mode enabled. Cache: {cache_enabled}")


@app.command()
def calculate_war(
    seasons: str = typer.Option(
        "2023",
        "--seasons",
        "-s",
        help="Seasons to analyze (comma-separated, e.g., '2022,2023')"
    ),
    weeks: Optional[str] = typer.Option(
        None,
        "--weeks",
        "-w",
        help="Weeks to include (comma-separated, e.g., '1,2,3' or '1-17')"
    ),
    positions: Optional[str] = typer.Option(
        None,
        "--positions",
        "-p",
        help="Positions to analyze (comma-separated, e.g., 'QB,RB,WR')"
    ),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (.csv or .json)"
    ),
    min_games: int = typer.Option(
        1,
        "--min-games",
        help="Minimum games played for WAR eligibility"
    ),
    teams: int = typer.Option(
        16,
        "--teams",
        help="Number of teams in league"
    ),
):
    """Calculate WAR for NFL players based on MPPR scoring."""
    
    # Parse inputs
    season_list = [int(s.strip()) for s in seasons.split(",")]
    
    if weeks:
        if "-" in weeks:
            start, end = weeks.split("-")
            week_list = list(range(int(start), int(end) + 1))
        else:
            week_list = [int(w.strip()) for w in weeks.split(",")]
    else:
        week_list = list(range(1, 18))  # Full season
    
    if positions:
        position_list = [pos.strip().upper() for pos in positions.split(",")]
    else:
        position_list = None
    
    console.print(f"\n[bold blue]🏈 Fantasy WAR Calculator[/bold blue]")
    console.print(f"Seasons: {season_list}")
    console.print(f"Weeks: {week_list}")
    console.print(f"Teams: {teams}")
    console.print(f"Min games: {min_games}")
    
    # Update league configuration
    league_config = LeagueConfig(
        name="Custom League",
        teams=teams,
        regular_season_weeks=week_list,
        minimum_games_played=min_games
    )
    
    # Initialize components
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        # Load NFL data
        task = progress.add_task("Loading NFL data...", total=None)
        data_loader = NFLDataLoader()
        stats_processor = StatsProcessor(league_config)
        
        try:
            # Load player statistics (always include IDP if R available, or if positions specified)
            include_idp = (position_list and any(pos in ["DT", "DE", "LB", "CB", "S"] for pos in position_list)) or data_loader.use_rpy2_fallback
            stats_df = data_loader.load_player_stats(season_list, weekly=True, include_idp=include_idp)
            progress.update(task, description="Processing statistics...")
            
            # Calculate fantasy points
            stats_with_points = stats_processor.calculate_fantasy_points(stats_df)
            
            # Filter positions if specified
            if position_list:
                stats_with_points = stats_with_points.filter(
                    stats_with_points["position"].is_in(position_list)
                )
            
            # Filter weeks
            stats_with_points = stats_with_points.filter(
                stats_with_points["week"].is_in(week_list)
            )
            
            progress.update(task, description="Calculating WAR...")
            
            # Calculate WAR
            war_calculator = WARCalculator(league_config)
            league_war = war_calculator.calculate_league_war(
                stats_with_points, 
                season_list, 
                week_list
            )
            
            progress.update(task, description="Complete!")
            
        except Exception as e:
            logger.error(f"Error during WAR calculation: {e}")
            console.print(f"[bold red]Error:[/bold red] {e}")
            raise typer.Exit(1)
    
    # Display results
    _display_war_results(league_war)
    
    # Save results if requested
    if output_file:
        _save_war_results(league_war, output_file)
        console.print(f"\n[bold green]✓[/bold green] Results saved to {output_file}")
    
    console.print(f"\n[bold green]✓ WAR calculation complete![/bold green]")


@app.command()
def auction_values(
    seasons: str = typer.Option(
        "2024",
        "--seasons",
        "-s", 
        help="Seasons to analyze"
    ),
    budget: int = typer.Option(
        200,
        "--budget",
        "-b",
        help="Total auction budget per team"
    ),
    positions: Optional[str] = typer.Option(
        None,
        "--positions",
        "-p",
        help="Positions to analyze (comma-separated, e.g., 'QB,RB,WR,TE,DT,DE,LB,CB,S')"
    ),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path"
    ),
    teams: int = typer.Option(
        16,
        "--teams",
        help="Number of teams in league"
    ),
):
    """Calculate auction values based on WAR analysis."""
    
    season_list = [int(s.strip()) for s in seasons.split(",")]
    
    # Parse positions
    position_list = None
    if positions:
        position_list = [pos.strip() for pos in positions.split(",")]
    
    console.print(f"\n[bold blue]💰 Auction Value Calculator[/bold blue]")
    console.print(f"Budget: ${budget} per team")
    if position_list:
        console.print(f"Positions: {', '.join(position_list)}")
    else:
        console.print("Positions: All standard positions")
    
    # Configure league
    league_config = LeagueConfig(name="Auction League", teams=teams)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        task = progress.add_task("Calculating auction values...", total=None)
        
        try:
            # Load data and calculate WAR
            data_loader = NFLDataLoader()
            stats_processor = StatsProcessor(league_config)
            
            # Load player statistics (always include IDP if R available, or if positions specified)
            include_idp = (position_list and any(pos in ["DT", "DE", "LB", "CB", "S"] for pos in position_list)) or data_loader.use_rpy2_fallback
            stats_df = data_loader.load_player_stats(season_list, weekly=True, include_idp=include_idp)
            stats_with_points = stats_processor.calculate_fantasy_points(stats_df)
            
            # Filter positions if specified
            if position_list:
                stats_with_points = stats_with_points.filter(
                    stats_with_points["position"].is_in(position_list)
                )
            
            war_calculator = WARCalculator(league_config)
            league_war = war_calculator.calculate_league_war(stats_with_points, season_list)
            
            progress.update(task, description="Calculating auction values...")
            
            # Calculate auction values
            auction_calc = AuctionValueCalculator(league_config, budget)
            auction_values = auction_calc.calculate_league_auction_values(league_war)
            
            progress.update(task, description="Complete!")
            
        except Exception as e:
            logger.error(f"Error calculating auction values: {e}")
            console.print(f"[bold red]Error:[/bold red] {e}")
            raise typer.Exit(1)
    
    # Display auction values
    _display_auction_values(auction_values)
    
    # Save if requested
    if output_file:
        _save_auction_values(auction_values, output_file)
        console.print(f"\n[bold green]✓[/bold green] Auction values saved to {output_file}")


@app.command()
def cache_info():
    """Display cache information and statistics."""
    
    console.print(f"\n[bold blue]🗄️  Cache Information[/bold blue]")
    
    stats = cache_manager.get_stats()
    
    if stats:
        table = Table(title="Cache Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Status", "Enabled" if stats['enabled'] else "Disabled")
        table.add_row("Directory", str(stats['directory']))
        table.add_row("Size (MB)", f"{stats['size_mb']:.2f}")
        table.add_row("Max Size (GB)", f"{stats['max_size_gb']:.1f}")
        table.add_row("Entry Count", str(stats['count']))
        table.add_row("TTL (days)", str(stats['ttl_days']))
        
        console.print(table)
    else:
        console.print("[yellow]Cache statistics unavailable[/yellow]")


@app.command()
def cache_clear():
    """Clear all cached data."""
    
    if typer.confirm("Are you sure you want to clear all cached data?"):
        success = cache_manager.clear_all()
        
        if success:
            console.print("[bold green]✓[/bold green] Cache cleared successfully")
        else:
            console.print("[bold red]✗[/bold red] Failed to clear cache")
    else:
        console.print("Cache clear cancelled")


@app.command()
def version():
    """Show version information."""
    from fantasy_war import __version__
    
    console.print(f"\n[bold blue]Fantasy WAR Calculator[/bold blue]")
    console.print(f"Version: {__version__}")
    console.print(f"Author: {settings.app_name}")


def _display_war_results(league_war):
    """Display WAR results in formatted tables."""
    
    console.print(f"\n[bold green]📊 WAR Results for {league_war.season}[/bold green]")
    
    # Top players overall
    top_players = league_war.top_players_overall[:20]
    
    if top_players:
        table = Table(title="Top 20 Players by WAR")
        table.add_column("Rank", justify="right", style="cyan")
        table.add_column("Player", style="white")
        table.add_column("Pos", style="yellow")
        table.add_column("WAR", justify="right", style="green")
        table.add_column("WAA", justify="right", style="blue")
        table.add_column("Games", justify="right")
        table.add_column("Avg Pts", justify="right")
        
        for i, war in enumerate(top_players, 1):
            table.add_row(
                str(i),
                war.player_name or war.player_id,
                war.position,
                f"{war.wins_above_replacement:.2f}",
                f"{war.wins_above_average:.2f}",
                str(war.games_played),
                f"{war.average_fantasy_points:.1f}"
            )
        
        console.print(table)
    
    # Position summaries
    console.print(f"\n[bold]Position Summaries[/bold]")
    
    pos_table = Table(title="WAR by Position")
    pos_table.add_column("Position", style="cyan")
    pos_table.add_column("Players", justify="right")
    pos_table.add_column("Total WAR", justify="right", style="green")
    pos_table.add_column("Avg WAR", justify="right", style="yellow")
    pos_table.add_column("Top Player WAR", justify="right", style="blue")
    
    for position, avg_war in league_war.average_war_per_position.items():
        pos_result = league_war.position_results.get(position)
        if pos_result and pos_result.player_wars:
            top_war = max(war.wins_above_replacement for war in pos_result.player_wars)
            total_war = sum(war.wins_above_replacement for war in pos_result.player_wars)
            
            pos_table.add_row(
                position,
                str(len(pos_result.player_wars)),
                f"{total_war:.1f}",
                f"{avg_war:.2f}",
                f"{top_war:.2f}"
            )
    
    console.print(pos_table)


def _display_auction_values(auction_values):
    """Display auction values in formatted table."""
    
    # Sort by auction value
    sorted_values = sorted(auction_values, key=lambda x: x.auction_value_dollars, reverse=True)
    
    console.print(f"\n[bold green]💰 Top 30 Auction Values[/bold green]")
    
    table = Table(title="Auction Values")
    table.add_column("Rank", justify="right", style="cyan")
    table.add_column("Player", style="white")
    table.add_column("Pos", style="yellow")
    table.add_column("Value", justify="right", style="green")
    table.add_column("WAR", justify="right", style="blue")
    table.add_column("Tier", justify="right")
    table.add_column("Sleeper", justify="center")
    table.add_column("Bust Risk", justify="center")
    
    for i, av in enumerate(sorted_values[:30], 1):
        sleeper_marker = "💎" if av.is_sleeper else ""
        bust_marker = "⚠️" if av.is_bust_risk else ""
        
        table.add_row(
            str(i),
            av.player_name or av.player_id,
            av.position,
            f"${av.auction_value_dollars:.0f}",
            f"{av.wins_above_replacement:.2f}",
            str(av.draft_tier),
            sleeper_marker,
            bust_marker
        )
    
    console.print(table)


def _save_war_results(league_war, output_file: Path):
    """Save WAR results to file."""
    
    # Collect all player results
    all_results = []
    
    for position, pos_result in league_war.position_results.items():
        for war in pos_result.player_wars:
            all_results.append({
                'player_id': war.player_id,
                'player_name': war.player_name,
                'position': war.position,
                'season': war.season,
                'games_played': war.games_played,
                'total_fantasy_points': war.total_fantasy_points,
                'average_fantasy_points': war.average_fantasy_points,
                'wins_above_replacement': war.wins_above_replacement,
                'wins_above_average': war.wins_above_average,
                'win_percentage': war.win_percentage,
                'expected_wins': war.expected_wins,
            })
    
    # Sort by WAR
    all_results.sort(key=lambda x: x['wins_above_replacement'], reverse=True)
    
    # Save to file
    if output_file.suffix.lower() == '.json':
        with open(output_file, 'w') as f:
            json.dump(all_results, f, indent=2, default=str)
    else:
        # Default to CSV
        if not output_file.suffix:
            output_file = output_file.with_suffix('.csv')
            
        with open(output_file, 'w', newline='') as f:
            if all_results:
                writer = csv.DictWriter(f, fieldnames=all_results[0].keys())
                writer.writeheader()
                writer.writerows(all_results)


def _save_auction_values(auction_values, output_file: Path):
    """Save auction values to file."""
    
    # Convert to dictionaries
    results = []
    for av in sorted(auction_values, key=lambda x: x.auction_value_dollars, reverse=True):
        results.append({
            'player_id': av.player_id,
            'player_name': av.player_name,
            'position': av.position,
            'auction_value_dollars': av.auction_value_dollars,
            'wins_above_replacement': av.wins_above_replacement,
            'war_rank_overall': av.war_rank_overall,
            'war_rank_position': av.war_rank_position,
            'draft_tier': av.draft_tier,
            'is_sleeper': av.is_sleeper,
            'is_bust_risk': av.is_bust_risk,
            'budget_percentage': av.budget_percentage,
        })
    
    # Save to file
    if output_file.suffix.lower() == '.json':
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
    else:
        # Default to CSV
        if not output_file.suffix:
            output_file = output_file.with_suffix('.csv')
            
        with open(output_file, 'w', newline='') as f:
            if results:
                writer = csv.DictWriter(f, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(results)


if __name__ == "__main__":
    app()