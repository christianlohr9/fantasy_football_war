"""League configuration for Fantasy WAR calculations.

Defines roster settings, league parameters, and position requirements
for calculating replacement level players and WAR values.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from fantasy_war.config.scoring import MPPRScoringSystem, mppr_scoring


class RosterRequirements(BaseModel):
    """Roster position requirements for a fantasy league."""
    
    # Offensive positions
    qb_min: int = Field(1, ge=0, description="Minimum QBs to start")
    qb_max: int = Field(1, ge=0, description="Maximum QBs to start")
    
    rb_min: int = Field(1, ge=0, description="Minimum RBs to start")
    rb_max: int = Field(2, ge=0, description="Maximum RBs to start")
    
    wr_min: int = Field(2, ge=0, description="Minimum WRs to start")
    wr_max: int = Field(4, ge=0, description="Maximum WRs to start")
    
    te_min: int = Field(1, ge=0, description="Minimum TEs to start")
    te_max: int = Field(2, ge=0, description="Maximum TEs to start")
    
    # Special teams positions
    pk_min: int = Field(1, ge=0, description="Minimum Kickers to start")
    pk_max: int = Field(1, ge=0, description="Maximum Kickers to start")
    
    pn_min: int = Field(1, ge=0, description="Minimum Punters to start")
    pn_max: int = Field(1, ge=0, description="Maximum Punters to start")
    
    # Individual defensive positions
    dt_min: int = Field(2, ge=0, description="Minimum Defensive Tackles to start")
    dt_max: int = Field(3, ge=0, description="Maximum Defensive Tackles to start")
    
    de_min: int = Field(2, ge=0, description="Minimum Defensive Ends to start")
    de_max: int = Field(3, ge=0, description="Maximum Defensive Ends to start")
    
    lb_min: int = Field(1, ge=0, description="Minimum Linebackers to start")
    lb_max: int = Field(3, ge=0, description="Maximum Linebackers to start")
    
    cb_min: int = Field(2, ge=0, description="Minimum Cornerbacks to start")
    cb_max: int = Field(4, ge=0, description="Maximum Cornerbacks to start")
    
    s_min: int = Field(2, ge=0, description="Minimum Safeties to start")
    s_max: int = Field(3, ge=0, description="Maximum Safeties to start")
    
    # Flex constraints
    offensive_flex_max: int = Field(7, description="Max QB/RB/WR/TE players total")
    total_idp: int = Field(12, description="Total IDP players required")
    total_starters: int = Field(21, description="Total starting players")
    
    # Validation removed for compatibility
    
    def get_position_requirements(self, position: str) -> tuple[int, int]:
        """Get min/max requirements for a specific position.
        
        Args:
            position: Position code (QB, RB, WR, TE, PK, PN, DT, DE, LB, CB, S)
            
        Returns:
            Tuple of (min_required, max_allowed) for the position
        """
        position_map = {
            'QB': (self.qb_min, self.qb_max),
            'RB': (self.rb_min, self.rb_max),
            'WR': (self.wr_min, self.wr_max),
            'TE': (self.te_min, self.te_max),
            'PK': (self.pk_min, self.pk_max),
            'PN': (self.pn_min, self.pn_max),
            'DT': (self.dt_min, self.dt_max),
            'DE': (self.de_min, self.de_max),
            'LB': (self.lb_min, self.lb_max),
            'CB': (self.cb_min, self.cb_max),
            'S': (self.s_min, self.s_max),
        }
        return position_map.get(position, (0, 0))


class LeagueConfig(BaseModel):
    """Complete league configuration for WAR calculations."""
    
    # Basic league info
    name: str = Field("Fantasy Analytical League", description="League name")
    teams: int = Field(16, ge=4, le=32, description="Number of teams in league")
    
    # Season configuration
    regular_season_weeks: List[int] = Field(
        default_factory=lambda: list(range(1, 13)),
        description="List of regular season weeks"
    )
    playoff_weeks: List[int] = Field(
        default_factory=lambda: list(range(13, 18)),
        description="List of playoff weeks"
    )
    
    # Roster configuration
    roster: RosterRequirements = Field(default_factory=RosterRequirements)
    
    # Scoring system
    scoring: MPPRScoringSystem = Field(default_factory=lambda: mppr_scoring)
    
    # WAR calculation parameters
    minimum_games_played: int = Field(1, ge=1, description="Minimum games for WAR eligibility")
    use_expected_points: bool = Field(False, description="Use EPA-based expected points")
    
    def get_replacement_level_count(self, position: str) -> int:
        """Calculate replacement level player count for a position.
        
        For WAR calculations, replacement level is typically the worst
        startable player at each position across all teams.
        
        Args:
            position: Position code (QB, RB, WR, TE, etc.)
            
        Returns:
            Number of players at replacement level (teams * max_starters)
        """
        min_req, max_req = self.roster.get_position_requirements(position)
        return self.teams * max_req if max_req > 0 else 0
    
    def get_starter_pool_size(self, position: str) -> int:
        """Get total number of starters across all teams for a position.
        
        Args:
            position: Position code
            
        Returns:
            Total starters needed across all teams
        """
        min_req, max_req = self.roster.get_position_requirements(position)
        # Use max requirements to determine pool size
        return self.teams * max_req if max_req > 0 else 0
    
    def is_idp_position(self, position: str) -> bool:
        """Check if position is an Individual Defensive Player position.
        
        Args:
            position: Position code
            
        Returns:
            True if position is IDP (DT, DE, LB, CB, S)
        """
        return position in ['DT', 'DE', 'LB', 'CB', 'S']
    
    def get_all_positions(self) -> List[str]:
        """Get list of all positions used in this league.
        
        Returns:
            List of position codes
        """
        positions = []
        
        # Add positions that have roster requirements
        for pos in ['QB', 'RB', 'WR', 'TE', 'PK', 'PN', 'DT', 'DE', 'LB', 'CB', 'S']:
            min_req, max_req = self.roster.get_position_requirements(pos)
            if max_req > 0:
                positions.append(pos)
                
        return positions


# Default FAL league configuration
fal_league = LeagueConfig(
    name="Fantasy Analytical League",
    teams=16,
    regular_season_weeks=list(range(1, 13)),
    playoff_weeks=list(range(13, 18)),
)