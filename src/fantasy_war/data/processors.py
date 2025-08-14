"""Data processing and fantasy points calculation for NFL statistics."""

from typing import List, Optional, Dict, Any
from datetime import timedelta

import polars as pl
import numpy as np
from loguru import logger

from fantasy_war.config.scoring import mppr_scoring, Position
from fantasy_war.config.leagues import LeagueConfig
from fantasy_war.models.stats import WeeklyStats, OffensiveStats, DefensiveStats, KickingStats, PuntingStats
from fantasy_war.data.cache import cache_manager


class StatsProcessor:
    """Processes raw NFL statistics into fantasy-relevant metrics."""
    
    def __init__(self, league_config: LeagueConfig, scoring_system=None):
        """Initialize stats processor.
        
        Args:
            league_config: League configuration for scoring rules
            scoring_system: Custom scoring system, uses MPPR if None
        """
        self.league_config = league_config
        self.scoring = scoring_system or mppr_scoring
        
        logger.info(f"StatsProcessor initialized for {league_config.name}")
    
    def calculate_fantasy_points(self, stats_df: pl.DataFrame) -> pl.DataFrame:
        """Calculate MPPR fantasy points from raw statistics.
        
        Args:
            stats_df: DataFrame with raw NFL statistics
            
        Returns:
            DataFrame with fantasy points added
        """
        logger.info(f"Calculating fantasy points for {len(stats_df)} player-weeks")
        
        # Create a copy to avoid modifying original
        df = stats_df.clone()
        
        # Ensure required columns exist with defaults
        df = self._ensure_columns(df)
        
        # Calculate fantasy points by position
        df = df.with_columns([
            pl.when(pl.col("position").is_in(["QB", "RB", "WR", "TE"]))
            .then(self._calculate_offensive_points())
            .when(pl.col("position").is_in(["DT", "DE", "LB", "CB", "S"]))
            .then(self._calculate_defensive_points())
            .when(pl.col("position") == "PK")
            .then(self._calculate_kicking_points())
            .when(pl.col("position") == "PN")
            .then(self._calculate_punting_points())
            .otherwise(0.0)
            .alias("fantasy_points_mppr")
        ])
        
        # Add MPPR-specific adjustments
        df = self._apply_mppr_adjustments(df)
        
        logger.info("Fantasy points calculation completed")
        return df
    
    def _ensure_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Ensure all required columns exist with default values."""
        
        # Define required columns with defaults
        required_cols = {
            # Offensive stats
            "passing_yards": 0, "pass_attempts": 0, "completions": 0,
            "passing_tds": 0, "interceptions": 0, "passing_2pt_conversions": 0,
            "sacks": 0, "sack_yards": 0, "passing_first_downs": 0,
            
            "rushing_yards": 0, "carries": 0, "rushing_tds": 0,
            "rushing_2pt_conversions": 0, "rushing_first_downs": 0,
            
            "receiving_yards": 0, "targets": 0, "receptions": 0,
            "receiving_tds": 0, "receiving_2pt_conversions": 0, "receiving_first_downs": 0,
            
            "sack_fumbles": 0, "rushing_fumbles": 0, "receiving_fumbles": 0,
            "sack_fumbles_lost": 0, "rushing_fumbles_lost": 0, "receiving_fumbles_lost": 0,
            
            # Defensive stats
            "tackles": 0, "assists": 0, "tackles_for_loss": 0,
            "sacks_def": 0, "qb_hits": 0, "passes_defended": 0,
            "interceptions_def": 0, "fumble_recoveries": 0, "forced_fumbles": 0,
            "safeties": 0, "defensive_tds": 0,
            
            # Kicking stats
            "fg_made_0_19": 0, "fg_made_20_29": 0, "fg_made_30_39": 0,
            "fg_made_40_49": 0, "fg_made_50_59": 0, "fg_made_60_": 0,
            "fg_missed_0_19": 0, "fg_missed_20_29": 0, "fg_missed_30_39": 0,
            "fg_missed_40_49": 0, "fg_missed_50_59": 0, "fg_missed_60_": 0,
            "pat_made": 0, "pat_missed": 0, "pat_blocked": 0,
            
            # Punting stats
            "punts": 0, "punt_yards": 0, "punts_inside_20": 0, "punts_blocked": 0,
            
            # Game participation (for weekly data, assume 1 game per week entry)
            "games_played": 1.0, "games_started": 0.0,
        }
        
        # Add missing columns
        for col, default_val in required_cols.items():
            if col not in df.columns:
                df = df.with_columns(pl.lit(default_val).alias(col))
        
        # Map column names to match expected schema
        if "recent_team" in df.columns and "team" not in df.columns:
            df = df.with_columns(pl.col("recent_team").alias("team"))
        
        # Map NFL position abbreviations to fantasy positions
        df = self._normalize_positions(df)
            
        return df
    
    def _normalize_positions(self, df: pl.DataFrame) -> pl.DataFrame:
        """Normalize NFL position abbreviations to fantasy positions."""
        # Map NFL positions to standard fantasy positions
        position_mapping = {
            # Linebackers
            'ILB': 'LB',  # Inside Linebacker
            'MLB': 'LB',  # Middle Linebacker  
            'OLB': 'LB',  # Outside Linebacker
            
            # Safeties
            'FS': 'S',    # Free Safety
            'SS': 'S',    # Strong Safety
            
            # Defensive positions already mapped correctly: DE, DT, CB
            # Offensive positions already correct: QB, RB, WR, TE
        }
        
        # Apply position mapping
        position_expr = pl.col("position")
        for nfl_pos, fantasy_pos in position_mapping.items():
            position_expr = position_expr.str.replace(nfl_pos, fantasy_pos)
        
        df = df.with_columns(position_expr.alias("position"))
        
        logger.debug(f"Position mapping applied. Unique positions: {sorted(df['position'].unique().to_list())}")
        return df
    
    def _calculate_offensive_points(self) -> pl.Expr:
        """Calculate offensive fantasy points using MPPR scoring."""
        
        return (
            # Passing
            (pl.col("passing_yards") * self.scoring.offensive.passing_yards) +
            (pl.col("pass_attempts") * self.scoring.offensive.pass_attempts) +  # Negative
            (pl.col("completions") * self.scoring.offensive.pass_completions) +
            (pl.col("passing_tds") * self.scoring.offensive.passing_tds) +
            (pl.col("interceptions") * self.scoring.offensive.interceptions) +  # Negative
            (pl.col("passing_2pt_conversions") * self.scoring.offensive.passing_2pt) +
            (pl.col("sacks") * self.scoring.offensive.qb_sacked) +  # Negative
            (pl.col("sack_yards") * self.scoring.offensive.sack_yards) +  # Negative
            
            # Rushing  
            (pl.col("rushing_yards") * self.scoring.offensive.rushing_yards) +
            (pl.col("carries") * self.scoring.offensive.rush_attempts) +  # Negative
            (pl.col("rushing_tds") * self.scoring.offensive.rushing_tds) +
            (pl.col("rushing_2pt_conversions") * self.scoring.offensive.rushing_2pt) +
            
            # Receiving
            (pl.col("receiving_yards") * self.scoring.offensive.receiving_yards) +
            (pl.col("targets") * self.scoring.offensive.targets) +  # Negative
            (pl.col("receptions") * self.scoring.offensive.receptions) +
            (pl.col("receiving_tds") * self.scoring.offensive.receiving_tds) +
            (pl.col("receiving_2pt_conversions") * self.scoring.offensive.receiving_2pt) +
            
            # Fumbles
            ((pl.col("sack_fumbles") + pl.col("rushing_fumbles") + pl.col("receiving_fumbles")) * 
             self.scoring.offensive.fumbles_lost) +  # Negative
            
            # First downs
            ((pl.col("passing_first_downs") + pl.col("rushing_first_downs") + pl.col("receiving_first_downs")) *
             self.scoring.offensive.first_downs)
        )
    
    def _calculate_defensive_points(self) -> pl.Expr:
        """Calculate IDP fantasy points using position-specific scoring."""
        
        # Base defensive scoring (same for all IDP positions)
        base_points = (
            (pl.col("forced_fumbles") * self.scoring.defensive.forced_fumbles) +
            (pl.col("fumble_recoveries") * self.scoring.defensive.fumble_recoveries) +
            (pl.col("interceptions_def") * self.scoring.defensive.interceptions) +
            (pl.col("sacks_def") * self.scoring.defensive.sacks) +  # Note: negative in MPPR
            (pl.col("qb_hits") * self.scoring.defensive.qb_hits) +
            (pl.col("tackles_for_loss") * self.scoring.defensive.tackles_for_loss) +
            (pl.col("safeties") * self.scoring.defensive.safeties) +
            (pl.col("defensive_tds") * self.scoring.defensive.defensive_tds)
        )
        
        # Position-specific tackle and assist scoring
        position_points = (
            pl.when(pl.col("position") == "DT")
            .then(
                (pl.col("tackles") * self.scoring.defensive.dt_tackles) +
                (pl.col("assists") * self.scoring.defensive.dt_assists) +
                (pl.col("passes_defended") * self.scoring.defensive.dt_passes_defended)
            )
            .when(pl.col("position") == "DE")
            .then(
                (pl.col("tackles") * self.scoring.defensive.de_tackles) +
                (pl.col("assists") * self.scoring.defensive.de_assists) +
                (pl.col("passes_defended") * self.scoring.defensive.de_passes_defended)
            )
            .when(pl.col("position") == "LB")
            .then(
                (pl.col("tackles") * self.scoring.defensive.lb_tackles) +
                (pl.col("assists") * self.scoring.defensive.lb_assists) +
                (pl.col("passes_defended") * self.scoring.defensive.lb_passes_defended)
            )
            .when(pl.col("position") == "CB")
            .then(
                (pl.col("tackles") * self.scoring.defensive.cb_tackles) +
                (pl.col("assists") * self.scoring.defensive.cb_assists) +
                (pl.col("passes_defended") * self.scoring.defensive.cb_passes_defended)
            )
            .when(pl.col("position") == "S")
            .then(
                (pl.col("tackles") * self.scoring.defensive.s_tackles) +
                (pl.col("assists") * self.scoring.defensive.s_assists) +
                (pl.col("passes_defended") * self.scoring.defensive.s_passes_defended)
            )
            .otherwise(0.0)
        )
        
        return base_points + position_points
    
    def _calculate_kicking_points(self) -> pl.Expr:
        """Calculate kicker fantasy points with distance-based scoring."""
        
        return (
            # Field goals made by distance
            (pl.col("fg_made_0_19") * 3.0) +      # Custom scoring for short FGs
            (pl.col("fg_made_20_29") * 5.0) +
            (pl.col("fg_made_30_39") * 5.0) +
            (pl.col("fg_made_40_49") * 6.0) +
            (pl.col("fg_made_50_59") * 7.0) +
            (pl.col("fg_made_60_") * 7.0) +
            
            # Field goal misses (negative points)
            (pl.col("fg_missed_0_19") * self.scoring.kicking.fg_missed) +
            (pl.col("fg_missed_20_29") * self.scoring.kicking.fg_missed) +
            (pl.col("fg_missed_30_39") * self.scoring.kicking.fg_missed) +
            (pl.col("fg_missed_40_49") * self.scoring.kicking.fg_missed) +
            (pl.col("fg_missed_50_59") * self.scoring.kicking.fg_missed) +
            (pl.col("fg_missed_60_") * self.scoring.kicking.fg_missed) +
            
            # Extra points
            (pl.col("pat_made") * self.scoring.kicking.extra_points) +
            (pl.col("pat_missed") * self.scoring.kicking.extra_points_missed) +
            (pl.col("pat_blocked") * self.scoring.kicking.extra_points_missed)
        )
    
    def _calculate_punting_points(self) -> pl.Expr:
        """Calculate punter fantasy points."""
        
        return (
            (pl.col("punts") * self.scoring.punting.punts) +  # Negative
            (pl.col("punt_yards") * self.scoring.punting.punt_yards) +
            (pl.col("punts_inside_20") * self.scoring.punting.punts_inside_20) +
            (pl.col("punts_blocked") * self.scoring.punting.punts_blocked)  # Negative
        )
    
    def _apply_mppr_adjustments(self, df: pl.DataFrame) -> pl.DataFrame:
        """Apply MPPR-specific adjustments to fantasy points."""
        
        # Calculate alternative scoring systems for comparison
        df = df.with_columns([
            # Standard PPR equivalent (for comparison)
            pl.when(pl.col("position").is_in(["QB", "RB", "WR", "TE"]))
            .then(
                (pl.col("passing_yards") * 0.04) +
                (pl.col("rushing_yards") * 0.1) +
                (pl.col("receiving_yards") * 0.1) +
                (pl.col("receptions") * 1.0) +  # Standard PPR
                (pl.col("passing_tds") * 4.0) +
                (pl.col("rushing_tds") * 6.0) +
                (pl.col("receiving_tds") * 6.0) +
                (pl.col("interceptions") * -2.0)
            )
            .otherwise(0.0)
            .alias("fantasy_points_ppr_comparison"),
            
            # Expected points (use MPPR as default since total_fantasy_points_exp not available)
            pl.col("fantasy_points_mppr").alias("fantasy_points_expected")
        ])
        
        return df
    
    def aggregate_season_stats(self, weekly_df: pl.DataFrame) -> pl.DataFrame:
        """Aggregate weekly stats to season totals.
        
        Args:
            weekly_df: DataFrame with weekly statistics
            
        Returns:
            DataFrame with season-aggregated statistics
        """
        logger.info("Aggregating weekly stats to season totals")
        
        # Group by player and season, sum most stats
        season_df = (
            weekly_df
            .group_by(["player_id", "season", "position"])
            .agg([
                # Game participation
                pl.col("games_played").sum().alias("games_played"),
                pl.col("games_started").sum().alias("games_started"),
                pl.len().alias("weeks_with_stats"),
                
                # Offensive stats
                pl.col("passing_yards").sum(),
                pl.col("pass_attempts").sum(),
                pl.col("completions").sum(),
                pl.col("passing_tds").sum(),
                pl.col("interceptions").sum(),
                pl.col("rushing_yards").sum(),
                pl.col("carries").sum(),
                pl.col("rushing_tds").sum(),
                pl.col("receiving_yards").sum(),
                pl.col("targets").sum(),
                pl.col("receptions").sum(),
                pl.col("receiving_tds").sum(),
                
                # Defensive stats
                pl.col("tackles").sum(),
                pl.col("assists").sum(),
                pl.col("sacks_def").sum(),
                pl.col("interceptions_def").sum(),
                pl.col("forced_fumbles").sum(),
                
                # Fantasy points
                pl.col("fantasy_points_mppr").sum().alias("total_fantasy_points_mppr"),
                pl.col("fantasy_points_mppr").mean().alias("avg_fantasy_points_mppr"),
            ])
        )
        
        # Calculate per-game averages
        season_df = season_df.with_columns([
            (pl.col("total_fantasy_points_mppr") / pl.col("games_played")).alias("fantasy_points_per_game"),
            (pl.col("total_fantasy_points_mppr") / pl.col("games_started")).alias("fantasy_points_per_start"),
        ])
        
        logger.info(f"Aggregated to {len(season_df)} player seasons")
        return season_df
    
    def filter_qualified_players(
        self, 
        stats_df: pl.DataFrame, 
        min_games: int = None,
        positions: Optional[List[str]] = None
    ) -> pl.DataFrame:
        """Filter to qualified players for WAR calculations.
        
        Args:
            stats_df: DataFrame with player statistics
            min_games: Minimum games played, uses league config if None
            positions: Positions to include, uses all if None
            
        Returns:
            Filtered DataFrame
        """
        min_games = min_games or self.league_config.minimum_games_played
        positions = positions or self.league_config.get_all_positions()
        
        logger.info(f"Filtering to qualified players: min_games={min_games}, positions={positions}")
        
        filtered_df = (
            stats_df
            .filter(
                (pl.col("games_played") >= min_games) &
                (pl.col("position").is_in(positions))
            )
        )
        
        logger.info(f"Filtered from {len(stats_df)} to {len(filtered_df)} qualified players")
        return filtered_df
    
    def calculate_positional_rankings(self, stats_df: pl.DataFrame) -> pl.DataFrame:
        """Add positional rankings based on fantasy points.
        
        Args:
            stats_df: DataFrame with fantasy points calculated
            
        Returns:
            DataFrame with ranking columns added
        """
        logger.info("Calculating positional rankings")
        
        # Add overall and positional rankings
        df_with_rankings = (
            stats_df
            .with_columns([
                # Overall ranking by fantasy points
                pl.col("total_fantasy_points_mppr").rank(method="ordinal", descending=True)
                .over("season").alias("rank_overall"),
                
                # Position ranking
                pl.col("total_fantasy_points_mppr").rank(method="ordinal", descending=True)
                .over(["season", "position"]).alias("rank_position"),
                
                # Percentile rankings
                pl.col("total_fantasy_points_mppr").rank(method="average", descending=True) / pl.len()
                .over("season").alias("percentile_overall"),
                
                pl.col("total_fantasy_points_mppr").rank(method="average", descending=True) / pl.len()
                .over(["season", "position"]).alias("percentile_position"),
            ])
        )
        
        return df_with_rankings