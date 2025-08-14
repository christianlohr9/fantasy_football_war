"""Statistical data models for Fantasy WAR system."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from fantasy_war.config.scoring import Position


class OffensiveStats(BaseModel):
    """Offensive statistics for QB, RB, WR, TE positions."""
    
    # Passing statistics
    pass_attempts: int = Field(0, ge=0)
    pass_completions: int = Field(0, ge=0) 
    passing_yards: int = Field(0)
    passing_tds: int = Field(0, ge=0)
    interceptions: int = Field(0, ge=0)
    passing_2pt_conversions: int = Field(0, ge=0)
    passing_first_downs: int = Field(0, ge=0)
    
    # Sack statistics (for QBs)
    sacks_taken: int = Field(0, ge=0)
    sack_yards_lost: int = Field(0, ge=0)  # Positive number for yards lost
    
    # Rushing statistics  
    rush_attempts: int = Field(0, ge=0)
    rushing_yards: int = Field(0)
    rushing_tds: int = Field(0, ge=0)
    rushing_2pt_conversions: int = Field(0, ge=0)
    rushing_first_downs: int = Field(0, ge=0)
    
    # Receiving statistics
    targets: int = Field(0, ge=0)
    receptions: int = Field(0, ge=0)
    receiving_yards: int = Field(0)
    receiving_tds: int = Field(0, ge=0)
    receiving_2pt_conversions: int = Field(0, ge=0)
    receiving_first_downs: int = Field(0, ge=0)
    
    # Fumble statistics
    fumbles: int = Field(0, ge=0)  # Fumbles committed
    fumbles_lost: int = Field(0, ge=0)  # Fumbles lost to opponent
    fumble_recoveries_own: int = Field(0, ge=0)  # Own fumbles recovered
    fumble_recovery_yards: int = Field(0)  # Yards on fumble recoveries
    fumble_recovery_tds: int = Field(0, ge=0)  # TDs on fumble recoveries
    
    # Other statistics
    penalty_yards: int = Field(0, ge=0)
    
    # Validation can be added later - removed for initial compatibility


class DefensiveStats(BaseModel):
    """Individual Defensive Player (IDP) statistics."""
    
    # Tackle statistics  
    tackles: int = Field(0, ge=0)
    assists: int = Field(0, ge=0)
    tackles_for_loss: int = Field(0, ge=0)
    
    # Pass rush statistics
    sacks: int = Field(0, ge=0)
    sack_yards: int = Field(0, ge=0)  # Positive yards gained from sacks
    qb_hits: int = Field(0, ge=0)
    
    # Coverage statistics
    passes_defended: int = Field(0, ge=0)
    interceptions: int = Field(0, ge=0)
    interception_yards: int = Field(0)
    interception_tds: int = Field(0, ge=0)
    
    # Fumble statistics
    forced_fumbles: int = Field(0, ge=0)
    fumble_recoveries: int = Field(0, ge=0)  # Opponent fumbles recovered
    fumble_recovery_yards: int = Field(0)
    fumble_recovery_tds: int = Field(0, ge=0)
    fumbles_own: int = Field(0, ge=0)  # Own fumbles committed
    fumble_recoveries_own: int = Field(0, ge=0)  # Own fumbles recovered
    own_fumble_recovery_yards: int = Field(0)
    
    # Special defensive plays
    safeties: int = Field(0, ge=0)
    defensive_tds: int = Field(0, ge=0)  # All defensive TDs
    defensive_conversions: int = Field(0, ge=0)  # Return conversions
    safeties_1pt: int = Field(0, ge=0)  # 1-point safeties
    
    # Blocked kicks
    blocked_kicks: int = Field(0, ge=0)  # All blocked kicks
    blocked_punts: int = Field(0, ge=0)
    blocked_field_goals: int = Field(0, ge=0)
    blocked_extra_points: int = Field(0, ge=0)
    blocked_kick_tds: int = Field(0, ge=0)  # TDs on blocked kicks


class KickingStats(BaseModel):
    """Kicker (PK) statistics with field goal distance tracking."""
    
    # Field goal statistics by distance
    fg_made_0_19: int = Field(0, ge=0)
    fg_made_20_29: int = Field(0, ge=0)  
    fg_made_30_39: int = Field(0, ge=0)
    fg_made_40_49: int = Field(0, ge=0)
    fg_made_50_59: int = Field(0, ge=0)
    fg_made_60_plus: int = Field(0, ge=0)
    
    fg_missed_0_19: int = Field(0, ge=0)
    fg_missed_20_29: int = Field(0, ge=0)
    fg_missed_30_39: int = Field(0, ge=0) 
    fg_missed_40_49: int = Field(0, ge=0)
    fg_missed_50_59: int = Field(0, ge=0)
    fg_missed_60_plus: int = Field(0, ge=0)
    
    fg_blocked_0_19: int = Field(0, ge=0)
    fg_blocked_20_29: int = Field(0, ge=0)
    fg_blocked_30_39: int = Field(0, ge=0)
    fg_blocked_40_49: int = Field(0, ge=0) 
    fg_blocked_50_59: int = Field(0, ge=0)
    fg_blocked_60_plus: int = Field(0, ge=0)
    
    # Extra point statistics
    extra_points_made: int = Field(0, ge=0)
    extra_points_missed: int = Field(0, ge=0)
    extra_points_blocked: int = Field(0, ge=0)
    
    # Other kicking stats
    fumbles_special_teams: int = Field(0, ge=0)
    
    @property
    def total_fg_made(self) -> int:
        """Total field goals made."""
        return (
            self.fg_made_0_19 + self.fg_made_20_29 + self.fg_made_30_39 +
            self.fg_made_40_49 + self.fg_made_50_59 + self.fg_made_60_plus
        )
    
    @property 
    def total_fg_missed(self) -> int:
        """Total field goals missed."""
        return (
            self.fg_missed_0_19 + self.fg_missed_20_29 + self.fg_missed_30_39 +
            self.fg_missed_40_49 + self.fg_missed_50_59 + self.fg_missed_60_plus
        )
    
    @property
    def total_fg_blocked(self) -> int:
        """Total field goals blocked."""
        return (
            self.fg_blocked_0_19 + self.fg_blocked_20_29 + self.fg_blocked_30_39 +
            self.fg_blocked_40_49 + self.fg_blocked_50_59 + self.fg_blocked_60_plus
        )
    
    @property
    def fg_percentage(self) -> float:
        """Field goal make percentage."""
        total_attempts = self.total_fg_made + self.total_fg_missed + self.total_fg_blocked
        return self.total_fg_made / total_attempts if total_attempts > 0 else 0.0


class PuntingStats(BaseModel):
    """Punter (PN) statistics."""
    
    punts: int = Field(0, ge=0)
    punt_yards: int = Field(0, ge=0)
    punts_inside_20: int = Field(0, ge=0)
    punts_blocked: int = Field(0, ge=0)
    fumbles_special_teams: int = Field(0, ge=0)
    
    @property
    def punt_average(self) -> float:
        """Average yards per punt."""
        return self.punt_yards / self.punts if self.punts > 0 else 0.0
    
    # Validation removed for compatibility


class WeeklyStats(BaseModel):
    """Complete weekly statistics for a player."""
    
    # Metadata
    player_id: str = Field(..., description="Player identifier")
    season: int = Field(..., ge=1920, le=2030)
    week: int = Field(..., ge=1, le=18)
    position: Position = Field(..., description="Player position")
    team: Optional[str] = Field(None, description="Team abbreviation")
    opponent: Optional[str] = Field(None, description="Opponent team")
    
    # Game context
    games_played: float = Field(0.0, ge=0.0, le=1.0, description="Games played (0.0-1.0)")
    games_started: float = Field(0.0, ge=0.0, le=1.0, description="Games started (0.0-1.0)")
    
    # Position-specific statistics
    offensive: Optional[OffensiveStats] = None
    defensive: Optional[DefensiveStats] = None  
    kicking: Optional[KickingStats] = None
    punting: Optional[PuntingStats] = None
    
    # Calculated fantasy points
    fantasy_points_mppr: Optional[float] = None
    fantasy_points_expected: Optional[float] = None  # EPA-based expected points
    
    # Validation removed for compatibility


class SeasonStats(BaseModel):
    """Aggregated season statistics for a player."""
    
    # Metadata
    player_id: str = Field(..., description="Player identifier") 
    season: int = Field(..., ge=1920, le=2030)
    position: Position = Field(..., description="Player position")
    
    # Season totals
    games_played: int = Field(0, ge=0, le=17)
    games_started: int = Field(0, ge=0, le=17)
    weeks_with_stats: int = Field(0, ge=0, le=18, description="Weeks with recorded stats")
    
    # Aggregated statistics (same structure as weekly)
    offensive: Optional[OffensiveStats] = None
    defensive: Optional[DefensiveStats] = None
    kicking: Optional[KickingStats] = None
    punting: Optional[PuntingStats] = None
    
    # Season fantasy totals
    total_fantasy_points_mppr: float = Field(0.0)
    average_fantasy_points_mppr: float = Field(0.0)
    total_fantasy_points_expected: Optional[float] = None
    
    # Per-game averages
    fantasy_points_per_game: float = Field(0.0)
    fantasy_points_per_start: float = Field(0.0)
    
    # Validation removed for compatibility