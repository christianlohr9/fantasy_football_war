"""Player data models for Fantasy WAR system."""

from typing import Optional
from datetime import date
from pydantic import BaseModel, Field

from fantasy_war.config.scoring import Position


class PlayerInfo(BaseModel):
    """Basic player information and metadata."""
    
    # Identifiers
    player_id: str = Field(..., description="Unique player identifier (GSIS ID)")
    full_name: str = Field(..., description="Player's full name")
    display_name: Optional[str] = Field(None, description="Display name for UI")
    
    # NFL information
    position: Position = Field(..., description="Primary position")
    team: Optional[str] = Field(None, description="Current NFL team abbreviation")
    jersey_number: Optional[int] = Field(None, ge=0, le=99)
    
    # Physical attributes
    height_inches: Optional[int] = Field(None, ge=60, le=84)
    weight_lbs: Optional[int] = Field(None, ge=150, le=400)
    birth_date: Optional[date] = Field(None)
    
    # Career information
    rookie_year: Optional[int] = Field(None, ge=1920, le=2030)
    years_experience: Optional[int] = Field(None, ge=0, le=30)
    college: Optional[str] = Field(None)
    
    # Fantasy relevance
    is_active: bool = Field(True, description="Currently active in NFL")
    fantasy_relevant: bool = Field(True, description="Relevant for fantasy purposes")
    
    @property
    def age(self) -> Optional[int]:
        """Calculate current age from birth date."""
        if self.birth_date is None:
            return None
        
        from datetime import date
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )
    
    # Validation removed for compatibility


class Player(BaseModel):
    """Complete player model including info and current season context."""
    
    info: PlayerInfo = Field(..., description="Basic player information")
    season: int = Field(..., ge=1920, le=2030, description="Season year")
    week: Optional[int] = Field(None, ge=1, le=18, description="Current week if applicable")
    
    # Season context
    games_played: int = Field(0, ge=0, le=17, description="Games played this season")
    games_started: int = Field(0, ge=0, le=17, description="Games started this season")
    is_injured: bool = Field(False, description="Currently injured")
    is_suspended: bool = Field(False, description="Currently suspended")
    
    @property
    def player_id(self) -> str:
        """Convenience property for player ID."""
        return self.info.player_id
    
    @property
    def name(self) -> str:
        """Convenience property for display name."""
        return self.info.display_name or self.info.full_name
    
    @property
    def position(self) -> Position:
        """Convenience property for position."""
        return self.info.position
    
    @property
    def team(self) -> Optional[str]:
        """Convenience property for team."""
        return self.info.team
    
    # Validation removed for compatibility
    
    def __str__(self) -> str:
        """String representation of player."""
        team_str = f" ({self.team})" if self.team else ""
        return f"{self.name} - {self.position}{team_str}"
    
    def __repr__(self) -> str:
        """Detailed representation of player."""
        return (
            f"Player(id={self.player_id}, name='{self.name}', "
            f"position={self.position}, season={self.season})"
        )