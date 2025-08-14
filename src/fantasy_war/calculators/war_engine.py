"""Core WAR calculation engine for Fantasy Football."""

from typing import List, Dict, Optional, Tuple
import math
from datetime import datetime

import polars as pl
import numpy as np
from scipy import stats
from loguru import logger

from fantasy_war.config.leagues import LeagueConfig
from fantasy_war.config.scoring import Position, mppr_scoring
from fantasy_war.models.war_results import WARResult, PositionWAR, LeagueWAR
from fantasy_war.calculators.replacement import ReplacementLevelCalculator
from fantasy_war.calculators.win_probability import WinProbabilityCalculator
from fantasy_war.data.cache import cache_manager


class WARCalculator:
    """Main WAR calculation engine implementing the Fantasy Analytical League methodology."""
    
    def __init__(self, league_config: LeagueConfig):
        """Initialize WAR calculator.
        
        Args:
            league_config: League configuration with roster and scoring settings
        """
        self.league_config = league_config
        self.replacement_calc = ReplacementLevelCalculator(league_config)
        self.win_prob_calc = WinProbabilityCalculator(league_config)
        
        logger.info(f"WAR calculator initialized for {league_config.name}")
    
    def calculate_league_war(
        self, 
        stats_df: pl.DataFrame, 
        seasons: List[int],
        weeks: Optional[List[int]] = None
    ) -> LeagueWAR:
        """Calculate WAR for all players and positions in the league.
        
        Args:
            stats_df: DataFrame with player statistics and fantasy points
            seasons: List of seasons to analyze
            weeks: List of weeks to include, uses all if None
            
        Returns:
            Complete league WAR analysis
        """
        weeks = weeks or self.league_config.regular_season_weeks
        
        logger.info(f"Calculating league WAR for seasons {seasons}, weeks {weeks}")
        
        # Filter data to specified seasons and weeks
        filtered_stats = (
            stats_df
            .filter(
                (pl.col("season").is_in(seasons)) &
                (pl.col("week").is_in(weeks))
            )
        )
        
        # Calculate team scoring context for win probability
        team_context = self._calculate_team_scoring_context(filtered_stats)
        
        # Calculate WAR for each position
        position_results = {}
        for position in self.league_config.get_all_positions():
            logger.info(f"Calculating WAR for position: {position}")
            
            pos_war = self.calculate_position_war(
                filtered_stats, 
                position, 
                seasons,
                weeks,
                team_context
            )
            
            if pos_war and len(pos_war.player_wars) > 0:
                position_results[position] = pos_war
        
        # Create league-wide results
        league_war = LeagueWAR(
            season=min(seasons),  # Primary season
            league_name=self.league_config.name,
            total_teams=self.league_config.teams,
            weeks_analyzed=weeks,
            positions_analyzed=list(position_results.keys()),
            position_results=position_results,
        )
        
        # Calculate league-wide statistics
        self._calculate_league_statistics(league_war)
        
        logger.info(f"League WAR calculation completed for {len(position_results)} positions")
        return league_war
    
    def calculate_position_war(
        self,
        stats_df: pl.DataFrame,
        position: Position,
        seasons: List[int],
        weeks: List[int],
        team_context: Dict[str, float]
    ) -> Optional[PositionWAR]:
        """Calculate WAR for all players at a specific position.
        
        Args:
            stats_df: Player statistics DataFrame
            position: Position to calculate WAR for
            seasons: Seasons being analyzed
            weeks: Weeks being analyzed
            team_context: Team scoring context (mean, std)
            
        Returns:
            Position WAR results or None if no qualified players
        """
        # Filter to position and qualified players
        position_stats = (
            stats_df
            .filter(
                (pl.col("position") == position) &
                (pl.col("games_played") >= self.league_config.minimum_games_played)
            )
        )
        
        if len(position_stats) == 0:
            logger.warning(f"No qualified players found for position {position}")
            return None
        
        # Aggregate to season level for WAR calculations
        season_stats = self._aggregate_to_season(position_stats)
        
        # Determine replacement level
        replacement_info = self.replacement_calc.find_replacement_level(
            season_stats, position
        )
        
        if not replacement_info:
            logger.warning(f"Could not determine replacement level for {position}")
            return None
        
        # Calculate WAR for each player
        player_wars = []
        
        for player_data in season_stats.iter_rows(named=True):
            war_result = self._calculate_player_war(
                player_data,
                replacement_info,
                team_context,
                weeks
            )
            
            if war_result:
                player_wars.append(war_result)
        
        # Sort by WAR value
        player_wars.sort(key=lambda x: x.wins_above_replacement, reverse=True)
        
        # Create position results
        position_war = PositionWAR(
            position=position,
            season=min(seasons),
            total_teams=self.league_config.teams,
            starters_per_team=self.league_config.roster.get_position_requirements(position)[1],
            total_starter_spots=self.league_config.get_starter_pool_size(position),
            replacement_level_rank=replacement_info['rank'],
            replacement_player_id=replacement_info.get('player_id'),
            player_wars=player_wars
        )
        
        # Calculate position statistics
        self._calculate_position_statistics(position_war)
        
        logger.info(f"Calculated WAR for {len(player_wars)} players at {position}")
        return position_war
    
    def _calculate_player_war(
        self,
        player_data: Dict,
        replacement_info: Dict,
        team_context: Dict[str, float],
        weeks: List[int]
    ) -> Optional[WARResult]:
        """Calculate WAR for an individual player.
        
        Args:
            player_data: Dictionary with player statistics
            replacement_info: Replacement level information
            team_context: Team scoring context
            weeks: Weeks included in analysis
            
        Returns:
            WAR result for the player
        """
        try:
            # Calculate expected team score with this player
            player_fp = player_data['total_fantasy_points_mppr']
            avg_fp = player_data['avg_fantasy_points_mppr']
            games_played = player_data['games_played']
            
            # Calculate win probability using normal distribution
            # This replicates the pnorm function from the R script
            win_prob = self.win_prob_calc.calculate_win_probability(
                player_fp,
                team_context['team_avg_score'],
                team_context['team_score_std']
            )
            
            expected_wins = win_prob * games_played
            
            # Calculate replacement level comparison
            replacement_fp = replacement_info['avg_fantasy_points']
            replacement_win_prob = self.win_prob_calc.calculate_win_probability(
                replacement_fp,
                team_context['team_avg_score'], 
                team_context['team_score_std']
            )
            
            replacement_wins = replacement_win_prob * games_played
            
            # Calculate WAR and WAA
            wins_above_replacement = expected_wins - replacement_wins
            
            # WAA calculation (wins above average starter)
            avg_starter_info = replacement_info.get('avg_starter_info', {})
            if avg_starter_info:
                avg_starter_win_prob = self.win_prob_calc.calculate_win_probability(
                    avg_starter_info['avg_fantasy_points'],
                    team_context['team_avg_score'],
                    team_context['team_score_std']
                )
                avg_starter_wins = avg_starter_win_prob * games_played
                wins_above_average = expected_wins - avg_starter_wins
            else:
                wins_above_average = 0.0
            
            # Create WAR result
            war_result = WARResult(
                player_id=player_data['player_id'],
                season=player_data['season'],
                position=player_data['position'],
                player_name=player_data.get('player_name'),
                team=player_data.get('team'),
                games_played=games_played,
                weeks_analyzed=weeks,
                total_fantasy_points=player_fp,
                average_fantasy_points=avg_fp,
                win_percentage=win_prob,
                expected_wins=expected_wins,
                replacement_win_percentage=replacement_win_prob,
                replacement_expected_wins=replacement_wins,
                wins_above_replacement=wins_above_replacement,
                wins_above_average=wins_above_average,
                team_average_score=team_context['team_avg_score'],
                team_score_std=team_context['team_score_std'],
            )
            
            return war_result
            
        except Exception as e:
            logger.error(f"Error calculating WAR for player {player_data.get('player_id', 'unknown')}: {e}")
            return None
    
    def _calculate_team_scoring_context(self, stats_df: pl.DataFrame) -> Dict[str, float]:
        """Calculate team scoring context for win probability calculations.
        
        This replicates the team average weekly score calculations from the R script.
        
        Args:
            stats_df: Player statistics DataFrame
            
        Returns:
            Dictionary with team scoring mean and standard deviation
        """
        logger.info("Calculating team scoring context")
        
        # Get top players at each position (starter pool)
        team_scores = []
        
        for position in self.league_config.get_all_positions():
            min_req, max_req = self.league_config.roster.get_position_requirements(position)
            
            if max_req == 0:
                continue
            
            # Get top players at this position
            position_players = (
                stats_df
                .filter(pl.col("position") == position)
                .group_by("player_id")
                .agg([
                    pl.col("fantasy_points_mppr").sum().alias("total_points"),
                    pl.col("season").first(),
                    pl.col("position").first(),
                ])
                .sort("total_points", descending=True)
                .head(self.league_config.teams * max_req)
            )
            
            if len(position_players) > 0:
                # Calculate average points for this position group
                avg_points = position_players['total_points'].mean()
                std_points = position_players['total_points'].std() or 0.0
                
                # Weight by number of starters at this position
                for _ in range(max_req):
                    team_scores.append({
                        'position': position,
                        'avg_points': avg_points,
                        'std_points': std_points,
                    })
        
        # Calculate overall team context
        if team_scores:
            total_avg = sum(pos['avg_points'] for pos in team_scores)
            
            # Calculate combined standard deviation
            # Using sum of variances for independent positions
            total_variance = sum(pos['std_points']**2 for pos in team_scores)
            total_std = math.sqrt(total_variance)
            
        else:
            logger.warning("No team scoring context calculated, using defaults")
            total_avg = 100.0  # Default team score
            total_std = 20.0   # Default standard deviation
        
        context = {
            'team_avg_score': total_avg,
            'team_score_std': max(total_std, 1.0),  # Ensure non-zero std
        }
        
        logger.info(f"Team scoring context: avg={total_avg:.2f}, std={total_std:.2f}")
        return context
    
    def _aggregate_to_season(self, weekly_stats: pl.DataFrame) -> pl.DataFrame:
        """Aggregate weekly statistics to season totals for WAR calculation.
        
        Args:
            weekly_stats: Weekly player statistics
            
        Returns:
            Season-aggregated statistics
        """
        return (
            weekly_stats
            .group_by(["player_id", "season", "position"])
            .agg([
                pl.col("games_played").sum().alias("games_played"),
                pl.col("fantasy_points_mppr").sum().alias("total_fantasy_points_mppr"),
                pl.col("fantasy_points_mppr").mean().alias("avg_fantasy_points_mppr"),
                pl.col("player_name").first(),
                pl.col("team").first(),
                pl.len().alias("weeks_played"),
            ])
            .filter(pl.col("games_played") >= self.league_config.minimum_games_played)
        )
    
    def _calculate_position_statistics(self, position_war: PositionWAR):
        """Calculate statistical summary for position WAR results.
        
        Args:
            position_war: Position WAR results to analyze
        """
        if not position_war.player_wars:
            return
        
        war_values = [war.wins_above_replacement for war in position_war.player_wars]
        
        position_war.average_war = np.mean(war_values)
        position_war.median_war = np.median(war_values)
        position_war.std_dev_war = np.std(war_values, ddof=1)
        
        # Set top and worst performers (already sorted)
        position_war.top_performers = position_war.player_wars[:10]
        position_war.worst_performers = position_war.player_wars[-10:]
    
    def _calculate_league_statistics(self, league_war: LeagueWAR):
        """Calculate league-wide WAR statistics.
        
        Args:
            league_war: League WAR results to analyze
        """
        total_war = 0.0
        position_wars = {}
        
        for position, pos_result in league_war.position_results.items():
            pos_war_total = sum(war.wins_above_replacement for war in pos_result.player_wars)
            total_war += pos_war_total
            position_wars[position] = pos_war_total / len(pos_result.player_wars) if pos_result.player_wars else 0.0
        
        league_war.total_war_generated = total_war
        league_war.average_war_per_position = position_wars
        
        logger.info(f"League totals: {total_war:.2f} total WAR across {len(position_wars)} positions")