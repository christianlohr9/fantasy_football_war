"""Replacement level calculation for WAR analysis."""

from typing import Dict, List, Optional, Any
import polars as pl
import numpy as np
from loguru import logger

from fantasy_war.config.leagues import LeagueConfig
from fantasy_war.config.scoring import Position


class ReplacementLevelCalculator:
    """Calculates replacement level players for WAR analysis."""
    
    def __init__(self, league_config: LeagueConfig):
        """Initialize replacement level calculator.
        
        Args:
            league_config: League configuration with roster settings
        """
        self.league_config = league_config
        logger.info("Replacement level calculator initialized")
    
    def find_replacement_level(
        self, 
        stats_df: pl.DataFrame, 
        position: Position
    ) -> Optional[Dict[str, Any]]:
        """Find replacement level player matching R script methodology.
        
        Implements the exact approach from WAR_function.R lines 761-765, 828-832, etc:
        - Get top N players (teams * position_requirement)
        - Replacement is the WORST of these starters (lowest rank)
        - For 14 teams with 1 RB each: 14th ranked RB is replacement level
        
        Args:
            stats_df: DataFrame with player statistics
            position: Position to find replacement level for
            
        Returns:
            Dictionary with replacement level information matching R script
        """
        logger.info(f"Finding replacement level for {position} (R script methodology)")
        
        # Get position requirements
        min_req, max_req = self.league_config.roster.get_position_requirements(position)
        
        if max_req == 0:
            logger.warning(f"Position {position} has no roster requirements")
            return None
        
        # Calculate starter pool size (R script: teams * position_requirement)
        starter_pool_size = self.league_config.teams * max_req
        
        # Get all qualified players at this position, sorted by total fantasy points
        # This matches the R script's approach of group_by(player_id) |> summarise(total_pts = sum(...))
        position_players = (
            stats_df
            .filter(
                (pl.col("position") == position) &
                (pl.col("games_played") >= self.league_config.minimum_games_played)
            )
            .sort("total_fantasy_points_mppr", descending=True)
            .with_row_count("rank", offset=1)
        )
        
        if len(position_players) < starter_pool_size:
            logger.warning(
                f"Not enough qualified players at {position}: "
                f"need {starter_pool_size}, have {len(position_players)}"
            )
            # Use the worst available player as replacement
            replacement_rank = len(position_players)
        else:
            # Replacement is the worst starter (R script lines 828-832)
            # top_n(...) %>% top_n(-1,wt = pts) - gets the lowest of the top N
            replacement_rank = starter_pool_size
        
        # Get the starter pool (top N players)
        starter_pool = position_players.head(starter_pool_size)
        
        # Find replacement level player (worst of the starters)
        replacement_player = starter_pool.tail(1)  # Last player in starter pool
        
        if len(replacement_player) == 0:
            logger.error(f"Could not find replacement level player for {position}")
            return None
        
        replacement_data = replacement_player.row(0, named=True)
        
        # Calculate position averages for expected team score calculations
        # This is used in the R script's exp_team_score calculation
        position_avg_fp = starter_pool['avg_fantasy_points_mppr'].mean()
        
        # Calculate average starter info for WAA calculations (R script lines 783-789)
        avg_starter_points = starter_pool['total_fantasy_points_mppr'].mean()
        avg_starter_games = starter_pool['games_played'].mean()
        avg_starter_win_prob = 0.5  # This will be calculated properly in the WAR engine
        
        replacement_info = {
            'player_id': replacement_data['player_id'],
            'rank': replacement_rank,
            'total_starters': starter_pool_size,
            'avg_fantasy_points': replacement_data['avg_fantasy_points_mppr'],
            'total_fantasy_points': replacement_data['total_fantasy_points_mppr'],
            'games_played': replacement_data['games_played'],
            'position_avg_fantasy_points': position_avg_fp,  # For exp_team_score calculation
            'avg_starter_info': {
                'avg_fantasy_points': avg_starter_points / avg_starter_games,
                'total_fantasy_points': avg_starter_points,
                'games_played': avg_starter_games,
            },
            'avg_starter_win_prob': avg_starter_win_prob  # Will be updated in WAR calculation
        }
        
        logger.info(
            f"Replacement level for {position}: rank {replacement_rank}/{starter_pool_size} starters, "
            f"player {replacement_data.get('player_name', replacement_data['player_id'])}, "
            f"{replacement_info['avg_fantasy_points']:.2f} avg points, "
            f"position avg: {position_avg_fp:.2f}"
        )
        
        return replacement_info
    
    def find_flex_replacement_level(
        self,
        stats_df: pl.DataFrame,
        flex_positions: List[Position],
        flex_spots: int
    ) -> Optional[Dict[str, Any]]:
        """Find replacement level for flex positions (RB/WR/TE).
        
        This handles the complex flex calculations from the original R script
        where players compete across multiple positions for flex spots.
        
        Args:
            stats_df: DataFrame with player statistics
            flex_positions: List of positions eligible for flex
            flex_spots: Number of flex spots available league-wide
            
        Returns:
            Flex replacement level information
        """
        logger.info(f"Finding flex replacement level for {flex_positions}")
        
        # Get players already used in dedicated position slots
        used_players = set()
        
        for position in flex_positions:
            min_req, max_req = self.league_config.roster.get_position_requirements(position)
            
            if max_req > 0:
                # Get top players at dedicated positions
                position_starters = (
                    stats_df
                    .filter(pl.col("position") == position)
                    .sort("total_fantasy_points_mppr", descending=True)
                    .head(self.league_config.teams * max_req)
                )
                
                for player_id in position_starters['player_id']:
                    used_players.add(player_id)
        
        # Find eligible flex players (not already used in dedicated slots)
        flex_eligible = (
            stats_df
            .filter(
                (pl.col("position").is_in(flex_positions)) &
                (~pl.col("player_id").is_in(list(used_players))) &
                (pl.col("games_played") >= self.league_config.minimum_games_played)
            )
            .sort("total_fantasy_points_mppr", descending=True)
            .with_row_count("flex_rank", offset=1)
        )
        
        if len(flex_eligible) < flex_spots:
            logger.warning(f"Not enough flex eligible players: need {flex_spots}, have {len(flex_eligible)}")
            flex_replacement_rank = len(flex_eligible)
        else:
            flex_replacement_rank = flex_spots
        
        # Get flex replacement player
        flex_replacement = flex_eligible.filter(pl.col("flex_rank") == flex_replacement_rank)
        
        if len(flex_replacement) == 0:
            logger.error("Could not find flex replacement level player")
            return None
        
        replacement_data = flex_replacement.row(0, named=True)
        
        # Calculate flex starter average
        flex_starters = flex_eligible.head(flex_spots)
        avg_flex_points = flex_starters['total_fantasy_points_mppr'].mean()
        avg_flex_games = flex_starters['games_played'].mean()
        
        flex_replacement_info = {
            'player_id': replacement_data['player_id'],
            'rank': flex_replacement_rank,
            'total_starters': flex_spots,
            'avg_fantasy_points': replacement_data['avg_fantasy_points_mppr'],
            'total_fantasy_points': replacement_data['total_fantasy_points_mppr'],
            'games_played': replacement_data['games_played'],
            'positions_eligible': flex_positions,
            'avg_starter_info': {
                'avg_fantasy_points': avg_flex_points / avg_flex_games,
                'total_fantasy_points': avg_flex_points,
                'games_played': avg_flex_games,
            }
        }
        
        logger.info(
            f"Flex replacement level: rank {flex_replacement_rank}, "
            f"{replacement_info['avg_fantasy_points']:.2f} avg points"
        )
        
        return flex_replacement_info
    
    def calculate_positional_scarcity(self, stats_df: pl.DataFrame) -> Dict[Position, float]:
        """Calculate scarcity multiplier for each position.
        
        Positions with fewer quality players available should have
        higher scarcity values, making top players more valuable.
        
        Args:
            stats_df: DataFrame with all player statistics
            
        Returns:
            Dictionary mapping positions to scarcity multipliers
        """
        logger.info("Calculating positional scarcity")
        
        scarcity_multipliers = {}
        
        for position in self.league_config.get_all_positions():
            # Get qualified players at position
            position_players = (
                stats_df
                .filter(
                    (pl.col("position") == position) &
                    (pl.col("games_played") >= self.league_config.minimum_games_played)
                )
            )
            
            if len(position_players) == 0:
                scarcity_multipliers[position] = 1.0
                continue
            
            # Calculate scarcity based on standard deviation
            # More variance = more scarcity at the top
            points_std = position_players['total_fantasy_points_mppr'].std()
            points_mean = position_players['total_fantasy_points_mppr'].mean()
            
            # Get starter pool size
            _, max_req = self.league_config.roster.get_position_requirements(position)
            starter_pool_size = self.league_config.teams * max_req
            
            # Calculate scarcity: higher std and smaller starter pool = more scarcity
            if points_mean > 0 and starter_pool_size > 0:
                coefficient_of_variation = points_std / points_mean
                pool_factor = 100 / starter_pool_size  # Normalize to typical pool size
                
                scarcity = 1.0 + (coefficient_of_variation * pool_factor * 0.5)
                scarcity_multipliers[position] = min(scarcity, 2.0)  # Cap at 2x
            else:
                scarcity_multipliers[position] = 1.0
        
        logger.info(f"Position scarcity multipliers: {scarcity_multipliers}")
        return scarcity_multipliers
    
    def identify_breakpoint_tiers(
        self, 
        stats_df: pl.DataFrame, 
        position: Position,
        num_tiers: int = 5
    ) -> Dict[int, Dict[str, Any]]:
        """Identify natural breakpoints in player values for tiering.
        
        This helps identify where significant drops in value occur,
        useful for draft strategy and player evaluation.
        
        Args:
            stats_df: DataFrame with player statistics
            position: Position to analyze
            num_tiers: Number of tiers to create
            
        Returns:
            Dictionary mapping tier numbers to tier information
        """
        logger.info(f"Identifying value tiers for {position}")
        
        # Get position players sorted by fantasy points
        position_players = (
            stats_df
            .filter(
                (pl.col("position") == position) &
                (pl.col("games_played") >= self.league_config.minimum_games_played)
            )
            .sort("total_fantasy_points_mppr", descending=True)
            .with_row_count("rank", offset=1)
        )
        
        if len(position_players) < num_tiers:
            logger.warning(f"Not enough players for {num_tiers} tiers at {position}")
            num_tiers = max(1, len(position_players))
        
        points = position_players['total_fantasy_points_mppr'].to_numpy()
        
        # Calculate differences between consecutive players
        if len(points) > 1:
            point_diffs = np.diff(points)
            
            # Find largest drops in value (negative differences)
            largest_drops = np.argsort(point_diffs)[:num_tiers-1]
            largest_drops = np.sort(largest_drops) + 1  # Adjust for diff offset
            
            # Create tier boundaries
            tier_boundaries = [0] + list(largest_drops) + [len(points)]
        else:
            tier_boundaries = [0, len(points)]
        
        # Create tier information
        tiers = {}
        
        for i in range(len(tier_boundaries) - 1):
            start_idx = tier_boundaries[i]
            end_idx = tier_boundaries[i + 1]
            
            tier_players = position_players.slice(start_idx, end_idx - start_idx)
            
            if len(tier_players) > 0:
                tier_info = {
                    'tier_number': i + 1,
                    'start_rank': start_idx + 1,
                    'end_rank': end_idx,
                    'player_count': len(tier_players),
                    'avg_points': tier_players['total_fantasy_points_mppr'].mean(),
                    'min_points': tier_players['total_fantasy_points_mppr'].min(),
                    'max_points': tier_players['total_fantasy_points_mppr'].max(),
                    'players': tier_players['player_id'].to_list(),
                }
                
                tiers[i + 1] = tier_info
        
        logger.info(f"Created {len(tiers)} tiers for {position}")
        return tiers