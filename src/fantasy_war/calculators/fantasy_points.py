"""Fantasy points calculation utilities and MPPR scoring implementation."""

from typing import Dict, List, Optional, Any, Tuple
import polars as pl
from loguru import logger

from fantasy_war.config.scoring import MPPRScoringSystem, Position, mppr_scoring
from fantasy_war.models.stats import WeeklyStats, OffensiveStats, DefensiveStats, KickingStats


class FantasyPointsCalculator:
    """Calculates fantasy points using various scoring systems."""
    
    def __init__(self, scoring_system: MPPRScoringSystem = None):
        """Initialize fantasy points calculator.
        
        Args:
            scoring_system: Scoring system to use, defaults to MPPR
        """
        self.scoring = scoring_system or mppr_scoring
        logger.info("Fantasy points calculator initialized with MPPR scoring")
    
    def calculate_offensive_points(
        self, 
        stats: Dict[str, Any], 
        position: Position
    ) -> float:
        """Calculate offensive fantasy points for QB/RB/WR/TE.
        
        Args:
            stats: Dictionary with player statistics
            position: Player position
            
        Returns:
            Total offensive fantasy points
        """
        if position not in ["QB", "RB", "WR", "TE"]:
            return 0.0
        
        points = 0.0
        
        # Passing statistics (mainly for QBs, but RBs/WRs can have passing plays)
        points += stats.get('passing_yards', 0) * self.scoring.offensive.passing_yards
        points += stats.get('pass_attempts', 0) * self.scoring.offensive.pass_attempts  # Negative
        points += stats.get('completions', 0) * self.scoring.offensive.pass_completions
        points += stats.get('passing_tds', 0) * self.scoring.offensive.passing_tds
        points += stats.get('interceptions', 0) * self.scoring.offensive.interceptions  # Negative
        points += stats.get('passing_2pt_conversions', 0) * self.scoring.offensive.passing_2pt
        points += stats.get('sacks', 0) * self.scoring.offensive.qb_sacked  # Negative
        points += stats.get('sack_yards', 0) * self.scoring.offensive.sack_yards  # Negative
        
        # Rushing statistics
        points += stats.get('rushing_yards', 0) * self.scoring.offensive.rushing_yards
        points += stats.get('carries', 0) * self.scoring.offensive.rush_attempts  # Negative
        points += stats.get('rushing_tds', 0) * self.scoring.offensive.rushing_tds
        points += stats.get('rushing_2pt_conversions', 0) * self.scoring.offensive.rushing_2pt
        
        # Receiving statistics
        points += stats.get('receiving_yards', 0) * self.scoring.offensive.receiving_yards
        points += stats.get('targets', 0) * self.scoring.offensive.targets  # Negative
        points += stats.get('receptions', 0) * self.scoring.offensive.receptions
        points += stats.get('receiving_tds', 0) * self.scoring.offensive.receiving_tds
        points += stats.get('receiving_2pt_conversions', 0) * self.scoring.offensive.receiving_2pt
        
        # Fumbles
        fumbles_lost = (
            stats.get('sack_fumbles', 0) + 
            stats.get('rushing_fumbles', 0) + 
            stats.get('receiving_fumbles', 0)
        )
        points += fumbles_lost * self.scoring.offensive.fumbles_lost  # Negative
        
        # First downs
        first_downs = (
            stats.get('passing_first_downs', 0) +
            stats.get('rushing_first_downs', 0) +
            stats.get('receiving_first_downs', 0)
        )
        points += first_downs * self.scoring.offensive.first_downs
        
        # Fumble recoveries (own fumbles recovered)
        points += stats.get('fumble_recoveries_own', 0) * self.scoring.offensive.fumble_recoveries
        points += stats.get('fumble_recovery_yards', 0) * self.scoring.offensive.fumble_recovery_yards
        points += stats.get('fumble_recovery_tds', 0) * self.scoring.offensive.fumble_recovery_tds
        
        # Penalty yards
        points += stats.get('penalty_yards', 0) * self.scoring.offensive.penalty_yards  # Negative
        
        return points
    
    def calculate_defensive_points(
        self, 
        stats: Dict[str, Any], 
        position: Position
    ) -> float:
        """Calculate IDP fantasy points for defensive positions.
        
        Args:
            stats: Dictionary with player statistics
            position: Player position (DT, DE, LB, CB, S)
            
        Returns:
            Total defensive fantasy points
        """
        if position not in ["DT", "DE", "LB", "CB", "S"]:
            return 0.0
        
        points = 0.0
        
        # Base defensive statistics (same for all IDP positions)
        points += stats.get('forced_fumbles', 0) * self.scoring.defensive.forced_fumbles
        points += stats.get('fumble_recoveries', 0) * self.scoring.defensive.fumble_recoveries
        points += stats.get('fumble_recovery_yards', 0) * self.scoring.defensive.fumble_recovery_yards
        points += stats.get('interceptions', 0) * self.scoring.defensive.interceptions
        points += stats.get('interception_yards', 0) * self.scoring.defensive.interception_yards
        points += stats.get('sacks', 0) * self.scoring.defensive.sacks  # Note: negative in MPPR
        points += stats.get('sack_yards', 0) * self.scoring.defensive.sack_yards
        points += stats.get('qb_hits', 0) * self.scoring.defensive.qb_hits
        points += stats.get('tackles_for_loss', 0) * self.scoring.defensive.tackles_for_loss
        points += stats.get('safeties', 0) * self.scoring.defensive.safeties
        points += stats.get('defensive_tds', 0) * self.scoring.defensive.defensive_tds
        points += stats.get('defensive_conversions', 0) * self.scoring.defensive.defensive_conversions
        points += stats.get('safeties_1pt', 0) * self.scoring.defensive.safeties_1pt
        
        # Blocked kicks
        points += stats.get('blocked_fgs', 0) * self.scoring.defensive.blocked_fgs
        points += stats.get('blocked_punts', 0) * self.scoring.defensive.blocked_punts
        points += stats.get('blocked_extra_points', 0) * self.scoring.defensive.blocked_extra_points
        points += stats.get('blocked_fg_tds', 0) * self.scoring.defensive.blocked_fg_tds
        points += stats.get('blocked_punt_tds', 0) * self.scoring.defensive.blocked_punt_tds
        
        # Own fumbles
        points += stats.get('fumbles_on_defense', 0) * self.scoring.defensive.fumbles_on_defense  # Negative
        points += stats.get('own_fumble_recoveries', 0) * self.scoring.defensive.own_fumble_recoveries
        points += stats.get('own_fumble_recovery_yards', 0) * self.scoring.defensive.own_fumble_recovery_yards
        
        # Position-specific tackle and assist scoring
        tackles = stats.get('tackles', 0)
        assists = stats.get('assists', 0)
        passes_defended = stats.get('passes_defended', 0)
        
        if position == "DT":
            points += tackles * self.scoring.defensive.dt_tackles
            points += assists * self.scoring.defensive.dt_assists
            points += passes_defended * self.scoring.defensive.dt_passes_defended
        elif position == "DE":
            points += tackles * self.scoring.defensive.de_tackles
            points += assists * self.scoring.defensive.de_assists
            points += passes_defended * self.scoring.defensive.de_passes_defended
        elif position == "LB":
            points += tackles * self.scoring.defensive.lb_tackles
            points += assists * self.scoring.defensive.lb_assists
            points += passes_defended * self.scoring.defensive.lb_passes_defended
        elif position == "CB":
            points += tackles * self.scoring.defensive.cb_tackles
            points += assists * self.scoring.defensive.cb_assists
            points += passes_defended * self.scoring.defensive.cb_passes_defended
        elif position == "S":
            points += tackles * self.scoring.defensive.s_tackles
            points += assists * self.scoring.defensive.s_assists
            points += passes_defended * self.scoring.defensive.s_passes_defended
        
        return points
    
    def calculate_kicking_points(self, stats: Dict[str, Any]) -> float:
        """Calculate kicker fantasy points with distance-based scoring.
        
        Args:
            stats: Dictionary with kicker statistics
            
        Returns:
            Total kicking fantasy points
        """
        points = 0.0
        
        # Field goals made by distance
        points += stats.get('fg_made_0_19', 0) * 5.0
        points += stats.get('fg_made_20_29', 0) * 5.0
        points += stats.get('fg_made_30_39', 0) * 5.0
        points += stats.get('fg_made_40_49', 0) * 6.0
        points += stats.get('fg_made_50_59', 0) * 7.0
        points += stats.get('fg_made_60_', 0) * 7.0
        
        # Field goal misses (negative points)
        points += stats.get('fg_missed_0_19', 0) * self.scoring.kicking.fg_missed
        points += stats.get('fg_missed_20_29', 0) * self.scoring.kicking.fg_missed
        points += stats.get('fg_missed_30_39', 0) * self.scoring.kicking.fg_missed
        points += stats.get('fg_missed_40_49', 0) * self.scoring.kicking.fg_missed
        points += stats.get('fg_missed_50_59', 0) * self.scoring.kicking.fg_missed
        points += stats.get('fg_missed_60_', 0) * self.scoring.kicking.fg_missed
        
        # Extra points
        points += stats.get('pat_made', 0) * self.scoring.kicking.extra_points
        points += stats.get('pat_missed', 0) * self.scoring.kicking.extra_points_missed
        points += stats.get('pat_blocked', 0) * self.scoring.kicking.extra_points_missed
        
        # Special teams fumbles
        points += stats.get('fumbles_special_teams', 0) * self.scoring.kicking.fumbles_special_teams
        
        return points
    
    def calculate_punting_points(self, stats: Dict[str, Any]) -> float:
        """Calculate punter fantasy points.
        
        Args:
            stats: Dictionary with punter statistics
            
        Returns:
            Total punting fantasy points
        """
        points = 0.0
        
        points += stats.get('punts', 0) * self.scoring.punting.punts  # Negative
        points += stats.get('punt_yards', 0) * self.scoring.punting.punt_yards
        points += stats.get('punts_inside_20', 0) * self.scoring.punting.punts_inside_20
        points += stats.get('punts_blocked', 0) * self.scoring.punting.punts_blocked  # Negative
        points += stats.get('fumbles_special_teams', 0) * self.scoring.punting.fumbles_special_teams
        
        return points
    
    def calculate_total_fantasy_points(
        self, 
        stats: Dict[str, Any], 
        position: Position
    ) -> Dict[str, float]:
        """Calculate total fantasy points for a player.
        
        Args:
            stats: Dictionary with all player statistics
            position: Player position
            
        Returns:
            Dictionary with different fantasy point calculations
        """
        results = {
            'fantasy_points_mppr': 0.0,
            'fantasy_points_offensive': 0.0,
            'fantasy_points_defensive': 0.0,
            'fantasy_points_kicking': 0.0,
            'fantasy_points_punting': 0.0,
        }
        
        # Calculate position-appropriate points
        if position in ["QB", "RB", "WR", "TE"]:
            offensive_points = self.calculate_offensive_points(stats, position)
            results['fantasy_points_offensive'] = offensive_points
            results['fantasy_points_mppr'] = offensive_points
            
        elif position in ["DT", "DE", "LB", "CB", "S"]:
            defensive_points = self.calculate_defensive_points(stats, position)
            results['fantasy_points_defensive'] = defensive_points
            results['fantasy_points_mppr'] = defensive_points
            
        elif position == "PK":
            kicking_points = self.calculate_kicking_points(stats)
            results['fantasy_points_kicking'] = kicking_points
            results['fantasy_points_mppr'] = kicking_points
            
        elif position == "PN":
            punting_points = self.calculate_punting_points(stats)
            results['fantasy_points_punting'] = punting_points
            results['fantasy_points_mppr'] = punting_points
        
        return results
    
    def calculate_alternative_scoring_systems(
        self, 
        stats: Dict[str, Any], 
        position: Position
    ) -> Dict[str, float]:
        """Calculate fantasy points using alternative scoring systems for comparison.
        
        Args:
            stats: Dictionary with player statistics
            position: Player position
            
        Returns:
            Dictionary with different scoring system results
        """
        results = {}
        
        if position in ["QB", "RB", "WR", "TE"]:
            # Standard PPR scoring
            ppr_points = (
                stats.get('passing_yards', 0) * 0.04 +
                stats.get('passing_tds', 0) * 4 +
                stats.get('interceptions', 0) * -2 +
                stats.get('rushing_yards', 0) * 0.1 +
                stats.get('rushing_tds', 0) * 6 +
                stats.get('receiving_yards', 0) * 0.1 +
                stats.get('receptions', 0) * 1.0 +  # PPR bonus
                stats.get('receiving_tds', 0) * 6 +
                stats.get('fumbles_lost', 0) * -2
            )
            results['fantasy_points_ppr'] = ppr_points
            
            # Half PPR scoring
            half_ppr_points = (
                stats.get('passing_yards', 0) * 0.04 +
                stats.get('passing_tds', 0) * 4 +
                stats.get('interceptions', 0) * -2 +
                stats.get('rushing_yards', 0) * 0.1 +
                stats.get('rushing_tds', 0) * 6 +
                stats.get('receiving_yards', 0) * 0.1 +
                stats.get('receptions', 0) * 0.5 +  # Half PPR
                stats.get('receiving_tds', 0) * 6 +
                stats.get('fumbles_lost', 0) * -2
            )
            results['fantasy_points_half_ppr'] = half_ppr_points
            
            # Standard (non-PPR) scoring
            standard_points = (
                stats.get('passing_yards', 0) * 0.04 +
                stats.get('passing_tds', 0) * 4 +
                stats.get('interceptions', 0) * -2 +
                stats.get('rushing_yards', 0) * 0.1 +
                stats.get('rushing_tds', 0) * 6 +
                stats.get('receiving_yards', 0) * 0.1 +
                stats.get('receiving_tds', 0) * 6 +
                stats.get('fumbles_lost', 0) * -2
            )
            results['fantasy_points_standard'] = standard_points
        
        return results
    
    def analyze_scoring_variance(
        self, 
        player_stats_list: List[Dict[str, Any]], 
        position: Position
    ) -> Dict[str, Any]:
        """Analyze variance in fantasy points across different games.
        
        Args:
            player_stats_list: List of game-by-game statistics
            position: Player position
            
        Returns:
            Dictionary with variance analysis
        """
        if not player_stats_list:
            return {}
        
        # Calculate fantasy points for each game
        game_points = []
        for stats in player_stats_list:
            points = self.calculate_total_fantasy_points(stats, position)
            game_points.append(points['fantasy_points_mppr'])
        
        game_points = [p for p in game_points if p is not None]
        
        if not game_points:
            return {}
        
        # Calculate variance metrics
        import statistics
        
        analysis = {
            'games_analyzed': len(game_points),
            'total_points': sum(game_points),
            'average_points': statistics.mean(game_points),
            'median_points': statistics.median(game_points),
            'std_deviation': statistics.stdev(game_points) if len(game_points) > 1 else 0.0,
            'min_points': min(game_points),
            'max_points': max(game_points),
            'coefficient_of_variation': 0.0,
            'boom_games': 0,  # Games > 1.5 * average
            'bust_games': 0,  # Games < 0.5 * average
        }
        
        if analysis['average_points'] > 0:
            analysis['coefficient_of_variation'] = analysis['std_deviation'] / analysis['average_points']
            
            boom_threshold = analysis['average_points'] * 1.5
            bust_threshold = analysis['average_points'] * 0.5
            
            analysis['boom_games'] = sum(1 for pts in game_points if pts > boom_threshold)
            analysis['bust_games'] = sum(1 for pts in game_points if pts < bust_threshold)
        
        return analysis