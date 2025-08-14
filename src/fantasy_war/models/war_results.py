"""WAR calculation results and auction value models."""

from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from fantasy_war.config.scoring import Position


class WARResult(BaseModel):
    """Individual player WAR calculation result."""
    
    # Player identification
    player_id: str = Field(..., description="Player identifier")
    season: int = Field(..., ge=1920, le=2030)
    position: Position = Field(..., description="Player position") 
    player_name: Optional[str] = Field(None, description="Player display name")
    team: Optional[str] = Field(None, description="Team abbreviation")
    
    # Game participation
    games_played: int = Field(0, ge=0, le=17)
    weeks_analyzed: List[int] = Field(default_factory=list, description="Weeks included in analysis")
    
    # Fantasy performance
    total_fantasy_points: float = Field(0.0, description="Total fantasy points scored")
    average_fantasy_points: float = Field(0.0, description="Average fantasy points per game")
    
    # WAR calculations
    win_percentage: float = Field(0.5, ge=0.0, le=1.0, description="Expected win percentage")
    expected_wins: float = Field(0.0, ge=0.0, description="Expected wins based on performance")
    
    # Replacement level comparisons
    replacement_win_percentage: float = Field(0.5, ge=0.0, le=1.0, description="Replacement level win percentage")
    replacement_expected_wins: float = Field(0.0, ge=0.0, description="Replacement level expected wins")
    
    # Final WAR metrics
    wins_above_replacement: float = Field(0.0, description="WAR - main metric")
    wins_above_average: float = Field(0.0, description="WAA - wins above average starter")
    
    # Context for calculations
    team_average_score: float = Field(0.0, description="Average team score used in calculations")
    team_score_std: float = Field(0.0, ge=0.0, description="Team score standard deviation")
    
    # Metadata
    calculated_at: datetime = Field(default_factory=datetime.utcnow)
    calculation_method: str = Field("normal_distribution", description="Method used for win probability")
    
    @property
    def war_per_game(self) -> float:
        """WAR per game played."""
        return self.wins_above_replacement / self.games_played if self.games_played > 0 else 0.0
    
    @property
    def is_replacement_level(self) -> bool:
        """Whether this player is at replacement level."""
        return abs(self.wins_above_replacement) < 0.01  # Within 0.01 WAR of replacement
    
    @property
    def is_above_average(self) -> bool:
        """Whether this player is above average."""
        return self.wins_above_average > 0.0
    
    # Validation removed for Pydantic V2 compatibility
    # TODO: Re-implement using Pydantic V2 field validators if needed
    # Expected wins validation: should not exceed games played


class PositionWAR(BaseModel):
    """WAR analysis results for all players at a specific position."""
    
    position: Position = Field(..., description="Position being analyzed")
    season: int = Field(..., ge=1920, le=2030)
    
    # League context
    total_teams: int = Field(..., gt=0, description="Number of teams in league")
    starters_per_team: int = Field(..., gt=0, description="Starters per team at this position")
    total_starter_spots: int = Field(..., gt=0, description="Total starter spots across league")
    
    # Replacement level information
    replacement_level_rank: int = Field(..., gt=0, description="Rank of replacement level player")
    replacement_player_id: Optional[str] = Field(None, description="ID of replacement level player")
    replacement_stats: Optional[Dict] = Field(None, description="Replacement level stats")
    
    # Position results
    player_wars: List[WARResult] = Field(default_factory=list, description="WAR for all players")
    
    # Position analytics
    average_war: float = Field(0.0, description="Average WAR for qualified players") 
    median_war: float = Field(0.0, description="Median WAR for qualified players")
    std_dev_war: float = Field(0.0, ge=0.0, description="Standard deviation of WAR")
    
    # Distribution information
    top_performers: List[WARResult] = Field(default_factory=list, description="Top 10 players by WAR")
    worst_performers: List[WARResult] = Field(default_factory=list, description="Bottom 10 players by WAR")
    
    @property
    def qualified_players(self) -> List[WARResult]:
        """Players who meet minimum games requirement."""
        return [war for war in self.player_wars if war.games_played >= 1]
    
    @property
    def starter_pool(self) -> List[WARResult]:
        """Players in the starter pool (top N players)."""
        qualified = self.qualified_players
        qualified.sort(key=lambda x: x.total_fantasy_points, reverse=True)
        return qualified[:self.total_starter_spots]
    
    # Validation removed for Pydantic V2 compatibility
    # TODO: Re-implement using Pydantic V2 field validators if needed
    # Sort WAR results by value descending
    
    # Validation removed for Pydantic V2 compatibility
    # TODO: Re-implement using Pydantic V2 field validators if needed
    # Set top_performers and worst_performers from player_wars


class AuctionValue(BaseModel):
    """Auction/draft value calculation for a player."""
    
    # Player identification  
    player_id: str = Field(..., description="Player identifier")
    season: int = Field(..., ge=1920, le=2030)
    position: Position = Field(..., description="Player position")
    player_name: Optional[str] = Field(None, description="Player display name")
    
    # WAR-based value
    wins_above_replacement: float = Field(0.0, description="Player's WAR value")
    war_rank_overall: int = Field(..., gt=0, description="Overall WAR rank across all positions")
    war_rank_position: int = Field(..., gt=0, description="WAR rank within position")
    
    # Auction value calculations
    auction_value_dollars: float = Field(0.0, ge=0.0, description="Estimated auction value in dollars")
    value_per_war: float = Field(0.0, ge=0.0, description="Dollars per WAR")
    
    # Relative value metrics
    value_over_replacement: float = Field(0.0, description="Value over replacement level")
    positional_scarcity_multiplier: float = Field(1.0, gt=0.0, description="Position scarcity adjustment")
    
    # Draft recommendations
    draft_tier: int = Field(1, ge=1, le=20, description="Draft tier (1=best)")
    is_sleeper: bool = Field(False, description="Undervalued player flag")
    is_bust_risk: bool = Field(False, description="Overvalued/risky player flag")
    
    # Context
    league_budget_total: int = Field(200, gt=0, description="Total auction budget per team")
    calculated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def value_per_dollar(self) -> float:
        """WAR value per auction dollar."""
        return self.wins_above_replacement / self.auction_value_dollars if self.auction_value_dollars > 0 else 0.0
    
    @property
    def budget_percentage(self) -> float:
        """Percentage of total budget this player represents.""" 
        return (self.auction_value_dollars / self.league_budget_total) * 100
    
    # Validation removed for Pydantic V2 compatibility
    # TODO: Re-implement using Pydantic V2 field validators if needed
    # Auction value validation: should not exceed 80% of total budget


class LeagueWAR(BaseModel):
    """Complete WAR analysis results for an entire league."""
    
    # League information
    season: int = Field(..., ge=1920, le=2030)
    league_name: str = Field(..., description="League identifier")
    total_teams: int = Field(..., gt=0)
    
    # Analysis scope
    weeks_analyzed: List[int] = Field(default_factory=list)
    positions_analyzed: List[Position] = Field(default_factory=list)
    
    # Position-level results
    position_results: Dict[Position, PositionWAR] = Field(default_factory=dict)
    
    # League-wide auction values
    auction_values: List[AuctionValue] = Field(default_factory=list)
    
    # League analytics
    total_war_generated: float = Field(0.0, description="Total WAR across all players")
    average_war_per_position: Dict[Position, float] = Field(default_factory=dict)
    
    # Market analysis
    total_auction_value: float = Field(0.0, description="Total auction value of all players")
    dollars_per_war_league_average: float = Field(0.0, description="League average $/WAR")
    
    # Metadata
    calculated_at: datetime = Field(default_factory=datetime.utcnow)
    calculation_version: str = Field("1.0.0", description="Version of calculation methodology")
    
    @property
    def top_players_overall(self) -> List[WARResult]:
        """Top 50 players by WAR across all positions."""
        all_wars = []
        for pos_result in self.position_results.values():
            all_wars.extend(pos_result.player_wars)
        
        all_wars.sort(key=lambda x: x.wins_above_replacement, reverse=True)
        return all_wars[:50]
    
    @property
    def most_valuable_positions(self) -> List[tuple[Position, float]]:
        """Positions ranked by total WAR generated."""
        pos_wars = []
        for position, result in self.position_results.items():
            total_war = sum(war.wins_above_replacement for war in result.player_wars)
            pos_wars.append((position, total_war))
        
        pos_wars.sort(key=lambda x: x[1], reverse=True)
        return pos_wars
    
    def get_position_results(self, position: Position) -> Optional[PositionWAR]:
        """Get WAR results for a specific position."""
        return self.position_results.get(position)
    
    def get_auction_value(self, player_id: str) -> Optional[AuctionValue]:
        """Get auction value for a specific player."""
        for av in self.auction_values:
            if av.player_id == player_id:
                return av
        return None