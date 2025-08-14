"""MPPR (Minus PPR) scoring system configuration.

This module implements the EPA-based Fantasy Analytical League (FAL) scoring system
based on the 10-Per-4 Framework and Estimated Points Added Framework.
"""

from typing import Dict, List, Literal, Union
from pydantic import BaseModel, Field

# Position type definitions
OffensivePosition = Literal["QB", "RB", "WR", "TE"]
DefensivePosition = Literal["DT", "DE", "LB", "CB", "S"]
SpecialTeamsPosition = Literal["PK", "PN"]  # Kicker, Punter
Position = Union[OffensivePosition, DefensivePosition, SpecialTeamsPosition]


class OffensiveScoring(BaseModel):
    """Offensive scoring rules for QB, RB, WR, TE positions."""
    
    # Passing statistics
    passing_tds: float = 4.0
    passing_yards: float = 0.2
    pass_attempts: float = -1.0  # Negative points for attempts
    pass_completions: float = 0.5
    interceptions: float = -10.0
    qb_sacked: float = -1.0  # Sacks taken
    sack_yards: float = -0.2  # Negative sack yardage
    passing_2pt: float = 3.0
    
    # Rushing statistics
    rushing_tds: float = 4.0
    rushing_yards: float = 0.2
    rush_attempts: float = -0.5  # Negative points for attempts
    rushing_2pt: float = 3.0
    
    # Receiving statistics
    receiving_tds: float = 4.0
    receiving_yards: float = 0.2
    receptions: float = 0.5
    targets: float = -1.0  # Negative points for targets
    receiving_2pt: float = 3.0
    
    # General offensive statistics
    fumbles_lost: float = -6.0
    fumble_recovery_tds: float = 4.0
    fumble_recoveries: float = 6.0  # Own fumble recoveries
    fumble_recovery_yards: float = 0.2
    penalty_yards: float = -0.2
    first_downs: float = 0.5


class DefensiveScoring(BaseModel):
    """Individual Defensive Player (IDP) scoring rules."""
    
    # Base IDP stats (all defensive positions)
    fumbles_on_defense: float = -4.0
    fumble_recoveries: float = 5.0  # Opponent fumble recoveries
    fumble_recovery_yards: float = 0.15
    forced_fumbles: float = 6.0
    interceptions: float = 6.0
    interception_yards: float = 0.15
    blocked_fg_tds: float = 6.0
    blocked_fgs: float = 5.0
    blocked_punt_tds: float = 6.0
    blocked_punts: float = 7.0
    blocked_extra_points: float = 2.0
    sacks: float = -0.5  # Negative for sack attempts (consistent with offensive)
    sack_yards: float = 0.2  # Positive for sack yardage gained
    qb_hits: float = 1.0
    tackles_for_loss: float = 2.0
    safeties: float = 2.0
    defensive_tds: float = 5.0
    defensive_conversions: float = 8.0  # Return conversions
    safeties_1pt: float = 4.0
    own_fumble_recoveries: float = 4.0  # Different from offensive
    own_fumble_recovery_yards: float = 0.15
    
    # Position-specific multipliers for tackles and assists
    dt_tackles: float = 2.5
    dt_assists: float = 1.5
    dt_passes_defended: float = 3.0
    
    de_tackles: float = 2.0
    de_assists: float = 1.0
    de_passes_defended: float = 3.0
    
    lb_tackles: float = 1.0
    lb_assists: float = 0.5
    lb_passes_defended: float = 3.0
    
    cb_tackles: float = 1.0
    cb_assists: float = 1.0
    cb_passes_defended: float = 4.0
    
    s_tackles: float = 1.0
    s_assists: float = 0.5
    s_passes_defended: float = 4.0


class KickingScoring(BaseModel):
    """Kicker (PK) scoring rules with distance-based scoring."""
    
    # Field goal scoring by distance ranges
    fg_0_29_base: float = -0.5  # Base for 0 yards
    fg_0_29_per_yard: float = 0.05  # Per yard over 0
    
    fg_30_39_base: float = 1.0  # Base for 30 yards
    fg_30_39_per_yard: float = 0.2  # Per yard over 30
    
    fg_40_plus_base: float = 3.0  # Base for 40 yards
    fg_40_plus_per_yard: float = 0.4  # Per yard over 40
    
    # Other kicking stats
    fg_missed: float = -6.0
    extra_points: float = 0.3
    extra_points_missed: float = -2.0
    fumbles_special_teams: float = -6.0


class PuntingScoring(BaseModel):
    """Punter (PN) scoring rules."""
    
    punts: float = -6.75  # Negative points per punt
    punt_yards: float = 0.15
    punts_inside_20: float = 2.0
    punts_blocked: float = -8.0
    fumbles_special_teams: float = -6.0


class MPPRScoringSystem(BaseModel):
    """Complete MPPR (Minus PPR) scoring system.
    
    Based on the Fantasy Analytical League (FAL) EPA-regressed scoring system
    that implements the 10-Per-4 Framework with negative points for attempts/targets.
    """
    
    offensive: OffensiveScoring = Field(default_factory=OffensiveScoring)
    defensive: DefensiveScoring = Field(default_factory=DefensiveScoring)
    kicking: KickingScoring = Field(default_factory=KickingScoring)
    punting: PuntingScoring = Field(default_factory=PuntingScoring)
    
    def get_position_scoring(self, position: Position) -> Dict[str, float]:
        """Get all relevant scoring rules for a specific position.
        
        Args:
            position: The player position (QB, RB, WR, TE, DT, DE, LB, CB, S, PK, PN)
            
        Returns:
            Dictionary mapping stat names to point values for the position
        """
        scoring = {}
        
        # All positions get basic offensive stats
        if position in ["QB", "RB", "WR", "TE"]:
            scoring.update(self.offensive.model_dump())
            
        # Add position-specific defensive stats
        elif position == "DT":
            scoring.update(self.defensive.model_dump())
            scoring.update({
                "tackles": self.defensive.dt_tackles,
                "assists": self.defensive.dt_assists,
                "passes_defended": self.defensive.dt_passes_defended,
            })
            
        elif position == "DE":
            scoring.update(self.defensive.model_dump())
            scoring.update({
                "tackles": self.defensive.de_tackles,
                "assists": self.defensive.de_assists,
                "passes_defended": self.defensive.de_passes_defended,
            })
            
        elif position == "LB":
            scoring.update(self.defensive.model_dump())
            scoring.update({
                "tackles": self.defensive.lb_tackles,
                "assists": self.defensive.lb_assists,
                "passes_defended": self.defensive.lb_passes_defended,
            })
            
        elif position == "CB":
            scoring.update(self.defensive.model_dump())
            scoring.update({
                "tackles": self.defensive.cb_tackles,
                "assists": self.defensive.cb_assists,
                "passes_defended": self.defensive.cb_passes_defended,
            })
            
        elif position == "S":
            scoring.update(self.defensive.model_dump())
            scoring.update({
                "tackles": self.defensive.s_tackles,
                "assists": self.defensive.s_assists,
                "passes_defended": self.defensive.s_passes_defended,
            })
            
        # Special teams positions
        elif position == "PK":
            scoring.update(self.kicking.model_dump())
            
        elif position == "PN":
            scoring.update(self.punting.model_dump())
            
        return scoring
    
    def calculate_field_goal_points(self, distance: int, made: bool) -> float:
        """Calculate field goal points based on distance and outcome.
        
        Args:
            distance: Field goal distance in yards
            made: Whether the field goal was made
            
        Returns:
            Points awarded for the field goal attempt
        """
        if not made:
            return self.kicking.fg_missed
            
        if distance < 30:
            return self.kicking.fg_0_29_base + (distance * self.kicking.fg_0_29_per_yard)
        elif distance < 40:
            return self.kicking.fg_30_39_base + ((distance - 30) * self.kicking.fg_30_39_per_yard)
        else:
            return self.kicking.fg_40_plus_base + ((distance - 40) * self.kicking.fg_40_plus_per_yard)


# Default MPPR scoring system instance
mppr_scoring = MPPRScoringSystem()