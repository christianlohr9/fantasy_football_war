"""Auction value calculations based on WAR analysis."""

import math
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from loguru import logger

from fantasy_war.config.leagues import LeagueConfig
from fantasy_war.config.scoring import Position
from fantasy_war.models.war_results import WARResult, PositionWAR, LeagueWAR, AuctionValue


class AuctionValueCalculator:
    """Calculates auction/draft values based on WAR methodology."""
    
    def __init__(self, league_config: LeagueConfig, total_budget: int = 200):
        """Initialize auction value calculator.
        
        Args:
            league_config: League configuration
            total_budget: Total auction budget per team
        """
        self.league_config = league_config
        self.total_budget = total_budget
        self.total_league_budget = total_budget * league_config.teams
        
        logger.info(f"Auction value calculator initialized with ${total_budget} per team budget")
    
    def calculate_league_auction_values(self, league_war: LeagueWAR) -> List[AuctionValue]:
        """Calculate auction values for all players in the league.
        
        Args:
            league_war: Complete league WAR analysis
            
        Returns:
            List of auction values for all players
        """
        logger.info("Calculating league-wide auction values")
        
        # Collect all WAR results
        all_war_results = []
        for pos_result in league_war.position_results.values():
            all_war_results.extend(pos_result.player_wars)
        
        # Sort by WAR value
        all_war_results.sort(key=lambda x: x.wins_above_replacement, reverse=True)
        
        # Calculate positional scarcity multipliers
        scarcity_multipliers = self._calculate_positional_scarcity(league_war)
        
        # Calculate base value per WAR
        base_value_per_war = self._calculate_base_value_per_war(all_war_results)
        
        # Generate auction values
        auction_values = []
        
        for i, war_result in enumerate(all_war_results):
            if war_result.wins_above_replacement <= 0:
                continue  # Skip replacement level and below players
            
            auction_value = self._calculate_individual_auction_value(
                war_result,
                base_value_per_war,
                scarcity_multipliers.get(war_result.position, 1.0),
                i + 1,  # Overall rank
                all_war_results
            )
            
            if auction_value:
                auction_values.append(auction_value)
        
        # Add auction values to league results
        league_war.auction_values = auction_values
        
        # Calculate league-wide auction statistics
        self._calculate_league_auction_stats(league_war)
        
        logger.info(f"Calculated auction values for {len(auction_values)} players")
        return auction_values
    
    def _calculate_base_value_per_war(self, war_results: List[WARResult]) -> float:
        """Calculate the base dollar value per WAR.
        
        This determines how much each unit of WAR is worth in auction dollars.
        
        Args:
            war_results: List of all WAR results, sorted by WAR descending
            
        Returns:
            Base dollars per WAR value
        """
        # Filter to positive WAR players (above replacement)
        positive_war_players = [war for war in war_results if war.wins_above_replacement > 0]
        
        if not positive_war_players:
            logger.warning("No positive WAR players found")
            return 1.0
        
        # Calculate total WAR above replacement
        total_war = sum(war.wins_above_replacement for war in positive_war_players)
        
        # Reserve some budget for replacement level players
        # Typically 60-70% of budget goes to above-replacement players
        available_budget = self.total_league_budget * 0.65
        
        # Calculate base value per WAR
        if total_war > 0:
            base_value = available_budget / total_war
        else:
            base_value = 1.0
        
        logger.info(f"Base value per WAR: ${base_value:.2f} (total WAR: {total_war:.2f})")
        return base_value
    
    def _calculate_positional_scarcity(self, league_war: LeagueWAR) -> Dict[Position, float]:
        """Calculate scarcity multipliers for each position.
        
        Positions with fewer quality options should have higher multipliers,
        making top players at those positions more valuable.
        
        Args:
            league_war: League WAR analysis
            
        Returns:
            Dictionary mapping positions to scarcity multipliers
        """
        scarcity_multipliers = {}
        
        for position, pos_result in league_war.position_results.items():
            if not pos_result.player_wars:
                scarcity_multipliers[position] = 1.0
                continue
            
            # Get WAR values for qualified players
            war_values = [war.wins_above_replacement for war in pos_result.qualified_players]
            
            if len(war_values) < 2:
                scarcity_multipliers[position] = 1.0
                continue
            
            # Calculate scarcity based on:
            # 1. Standard deviation (more variance = more scarcity at top)
            # 2. Drop-off from best to replacement level
            # 3. Number of startable players vs. league needs
            
            war_std = np.std(war_values)
            war_max = max(war_values)
            replacement_war = 0.0  # By definition
            
            # Drop-off factor
            dropoff_factor = war_max - replacement_war if war_max > 0 else 1.0
            
            # Depth factor (fewer players per starter spot = more scarcity)
            starter_spots = pos_result.total_starter_spots
            qualified_players = len(pos_result.qualified_players)
            depth_factor = starter_spots / max(qualified_players, starter_spots) if qualified_players > 0 else 1.0
            
            # Combine factors
            scarcity = 1.0 + (war_std * dropoff_factor * depth_factor * 0.1)
            scarcity = min(scarcity, 1.8)  # Cap at 1.8x multiplier
            
            scarcity_multipliers[position] = scarcity
        
        logger.info(f"Positional scarcity multipliers: {scarcity_multipliers}")
        return scarcity_multipliers
    
    def _calculate_individual_auction_value(
        self,
        war_result: WARResult,
        base_value_per_war: float,
        position_multiplier: float,
        overall_rank: int,
        all_war_results: List[WARResult]
    ) -> Optional[AuctionValue]:
        """Calculate auction value for an individual player.
        
        Args:
            war_result: Player's WAR result
            base_value_per_war: Base dollar value per WAR
            position_multiplier: Positional scarcity multiplier
            overall_rank: Player's overall rank by WAR
            all_war_results: All WAR results for context
            
        Returns:
            AuctionValue object or None if not valuable enough
        """
        if war_result.wins_above_replacement <= 0:
            return None
        
        # Calculate base auction value
        base_value = war_result.wins_above_replacement * base_value_per_war
        
        # Apply positional scarcity
        position_adjusted_value = base_value * position_multiplier
        
        # Apply rank-based adjustments (top players get premium)
        rank_multiplier = self._calculate_rank_multiplier(overall_rank)
        final_value = position_adjusted_value * rank_multiplier
        
        # Ensure minimum value for positive WAR players
        final_value = max(final_value, 1.0)
        
        # Cap at reasonable percentage of total budget
        max_value = self.total_budget * 0.6  # No player worth more than 60% of budget
        final_value = min(final_value, max_value)
        
        # Calculate positional rank
        position_rank = self._get_position_rank(war_result, all_war_results)
        
        # Determine draft tier (1 = elite, 5 = depth)
        draft_tier = self._calculate_draft_tier(overall_rank, final_value)
        
        # Identify sleepers and bust risks
        is_sleeper = self._is_sleeper_candidate(war_result, final_value, position_rank)
        is_bust_risk = self._is_bust_risk(war_result, final_value, overall_rank)
        
        auction_value = AuctionValue(
            player_id=war_result.player_id,
            season=war_result.season,
            position=war_result.position,
            player_name=war_result.player_name,
            wins_above_replacement=war_result.wins_above_replacement,
            war_rank_overall=overall_rank,
            war_rank_position=position_rank,
            auction_value_dollars=round(final_value, 0),
            value_per_war=base_value_per_war,
            value_over_replacement=final_value - 1.0,  # $1 = replacement level
            positional_scarcity_multiplier=position_multiplier,
            draft_tier=draft_tier,
            is_sleeper=is_sleeper,
            is_bust_risk=is_bust_risk,
            league_budget_total=self.total_budget,
        )
        
        return auction_value
    
    def _calculate_rank_multiplier(self, overall_rank: int) -> float:
        """Calculate rank-based value multiplier.
        
        Top players get a premium due to their scarcity and impact.
        
        Args:
            overall_rank: Player's overall rank by WAR
            
        Returns:
            Multiplier for rank-based premium/discount
        """
        if overall_rank <= 5:
            return 1.3  # Elite tier gets 30% premium
        elif overall_rank <= 12:
            return 1.2  # First round gets 20% premium
        elif overall_rank <= 24:
            return 1.1  # Second round gets 10% premium
        elif overall_rank <= 50:
            return 1.0  # No adjustment
        elif overall_rank <= 100:
            return 0.95  # Slight discount for depth
        else:
            return 0.9  # Deeper discount for late picks
    
    def _get_position_rank(
        self, 
        war_result: WARResult, 
        all_war_results: List[WARResult]
    ) -> int:
        """Get player's rank within their position.
        
        Args:
            war_result: Player's WAR result
            all_war_results: All WAR results
            
        Returns:
            Position rank (1-based)
        """
        position_players = [
            war for war in all_war_results 
            if war.position == war_result.position
        ]
        
        position_players.sort(key=lambda x: x.wins_above_replacement, reverse=True)
        
        for i, player in enumerate(position_players):
            if player.player_id == war_result.player_id:
                return i + 1
        
        return len(position_players) + 1
    
    def _calculate_draft_tier(self, overall_rank: int, auction_value: float) -> int:
        """Calculate draft tier based on rank and value.
        
        Args:
            overall_rank: Overall rank by WAR
            auction_value: Calculated auction value
            
        Returns:
            Draft tier (1 = elite, 5 = depth)
        """
        if overall_rank <= 12 and auction_value >= self.total_budget * 0.25:
            return 1  # Elite tier
        elif overall_rank <= 24 and auction_value >= self.total_budget * 0.15:
            return 2  # High-end starters
        elif overall_rank <= 50 and auction_value >= self.total_budget * 0.08:
            return 3  # Solid starters
        elif overall_rank <= 100 and auction_value >= self.total_budget * 0.04:
            return 4  # Flex/backup players
        else:
            return 5  # Depth/streaming options
    
    def _is_sleeper_candidate(
        self, 
        war_result: WARResult, 
        auction_value: float, 
        position_rank: int
    ) -> bool:
        """Identify potential sleeper picks.
        
        Args:
            war_result: Player's WAR result
            auction_value: Calculated auction value
            position_rank: Position rank
            
        Returns:
            True if player appears to be undervalued
        """
        # Simple sleeper criteria:
        # 1. Decent WAR but low auction value (value play)
        # 2. Not ranked too highly at position
        # 3. Has room for growth
        
        value_efficiency = war_result.wins_above_replacement / auction_value
        
        return (
            war_result.wins_above_replacement > 0.5 and  # Decent WAR
            auction_value < self.total_budget * 0.1 and  # Low cost
            position_rank > 10 and  # Not obvious choice
            value_efficiency > 0.05  # Good value per dollar
        )
    
    def _is_bust_risk(
        self, 
        war_result: WARResult, 
        auction_value: float, 
        overall_rank: int
    ) -> bool:
        """Identify potential bust risks.
        
        Args:
            war_result: Player's WAR result
            auction_value: Calculated auction value
            overall_rank: Overall rank
            
        Returns:
            True if player appears overvalued/risky
        """
        # Simple bust risk criteria:
        # 1. High auction value relative to WAR
        # 2. High draft position creates expectations
        # 3. Limited sample size or volatility
        
        value_efficiency = war_result.wins_above_replacement / auction_value
        
        return (
            overall_rank <= 24 and  # High draft position
            auction_value >= self.total_budget * 0.15 and  # Expensive
            value_efficiency < 0.03  # Poor value per dollar
        )
    
    def _calculate_league_auction_stats(self, league_war: LeagueWAR):
        """Calculate league-wide auction value statistics.
        
        Args:
            league_war: League WAR analysis to update
        """
        if not league_war.auction_values:
            return
        
        total_value = sum(av.auction_value_dollars for av in league_war.auction_values)
        total_war = sum(av.wins_above_replacement for av in league_war.auction_values)
        
        league_war.total_auction_value = total_value
        
        if total_war > 0:
            league_war.dollars_per_war_league_average = total_value / total_war
        else:
            league_war.dollars_per_war_league_average = 0.0
        
        logger.info(
            f"League auction stats: ${total_value:.0f} total value, "
            f"${league_war.dollars_per_war_league_average:.2f} per WAR"
        )
    
    def generate_draft_board(
        self, 
        auction_values: List[AuctionValue],
        sort_by: str = "auction_value"
    ) -> List[Dict[str, Any]]:
        """Generate a draft board with player rankings.
        
        Args:
            auction_values: List of auction values
            sort_by: How to sort ("auction_value", "war", "value_efficiency")
            
        Returns:
            Sorted list of players with draft information
        """
        if sort_by == "war":
            sorted_values = sorted(auction_values, key=lambda x: x.wins_above_replacement, reverse=True)
        elif sort_by == "value_efficiency":
            sorted_values = sorted(
                auction_values, 
                key=lambda x: x.wins_above_replacement / x.auction_value_dollars if x.auction_value_dollars > 0 else 0,
                reverse=True
            )
        else:  # Default to auction_value
            sorted_values = sorted(auction_values, key=lambda x: x.auction_value_dollars, reverse=True)
        
        draft_board = []
        
        for i, av in enumerate(sorted_values):
            draft_board.append({
                'rank': i + 1,
                'player_name': av.player_name or av.player_id,
                'position': av.position,
                'war': av.wins_above_replacement,
                'auction_value': av.auction_value_dollars,
                'position_rank': av.war_rank_position,
                'tier': av.draft_tier,
                'value_efficiency': av.value_per_dollar,
                'budget_percent': av.budget_percentage,
                'sleeper': av.is_sleeper,
                'bust_risk': av.is_bust_risk,
            })
        
        return draft_board
    
    def calculate_optimal_budget_allocation(
        self, 
        auction_values: List[AuctionValue]
    ) -> Dict[Position, Dict[str, Any]]:
        """Calculate optimal budget allocation by position.
        
        Args:
            auction_values: List of auction values
            
        Returns:
            Dictionary with budget recommendations by position
        """
        position_analysis = {}
        
        # Group by position
        by_position = {}
        for av in auction_values:
            if av.position not in by_position:
                by_position[av.position] = []
            by_position[av.position].append(av)
        
        # Analyze each position
        for position, pos_values in by_position.items():
            pos_values.sort(key=lambda x: x.auction_value_dollars, reverse=True)
            
            # Get starter requirements
            min_req, max_req = self.league_config.roster.get_position_requirements(position)
            
            # Calculate recommendations
            top_tier_value = sum(av.auction_value_dollars for av in pos_values[:max_req])
            mid_tier_value = sum(av.auction_value_dollars for av in pos_values[max_req:max_req*2]) if len(pos_values) > max_req else 0
            
            total_position_value = sum(av.auction_value_dollars for av in pos_values)
            
            position_analysis[position] = {
                'min_starters': min_req,
                'max_starters': max_req,
                'total_players': len(pos_values),
                'top_tier_cost': top_tier_value,
                'mid_tier_cost': mid_tier_value,
                'total_value': total_position_value,
                'avg_top_tier': top_tier_value / max_req if max_req > 0 else 0,
                'recommended_budget_pct': (total_position_value / sum(av.auction_value_dollars for av in auction_values)) * 100,
                'scarcity_rating': 'High' if len(pos_values) < max_req * 1.5 else 'Medium' if len(pos_values) < max_req * 2 else 'Low',
            }
        
        return position_analysis