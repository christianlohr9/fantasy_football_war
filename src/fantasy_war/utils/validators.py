"""Input validation utilities for Fantasy WAR system."""

from typing import List, Union
from datetime import datetime

from fantasy_war.config.scoring import Position


def validate_season(season: Union[int, str]) -> int:
    """Validate and normalize season input.
    
    Args:
        season: Season year
        
    Returns:
        Validated season as integer
        
    Raises:
        ValueError: If season is invalid
    """
    try:
        season_int = int(season)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid season: {season}. Must be a valid year.")
    
    current_year = datetime.now().year
    
    if season_int < 1920:
        raise ValueError(f"Season {season_int} too early. NFL data starts from 1920.")
    
    if season_int > current_year + 1:
        raise ValueError(f"Season {season_int} is in the future. Current year: {current_year}")
    
    return season_int


def validate_week(week: Union[int, str]) -> int:
    """Validate and normalize week input.
    
    Args:
        week: NFL week number
        
    Returns:
        Validated week as integer
        
    Raises:
        ValueError: If week is invalid
    """
    try:
        week_int = int(week)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid week: {week}. Must be a valid week number.")
    
    if week_int < 1 or week_int > 18:
        raise ValueError(f"Week {week_int} is invalid. Must be between 1 and 18.")
    
    return week_int


def validate_position(position: Union[str, Position]) -> Position:
    """Validate and normalize position input.
    
    Args:
        position: Player position
        
    Returns:
        Validated position
        
    Raises:
        ValueError: If position is invalid
    """
    if isinstance(position, str):
        position = position.upper().strip()
    
    valid_positions = ["QB", "RB", "WR", "TE", "PK", "PN", "DT", "DE", "LB", "CB", "S"]
    
    if position not in valid_positions:
        raise ValueError(
            f"Invalid position: {position}. "
            f"Valid positions: {', '.join(valid_positions)}"
        )
    
    return position


def validate_seasons_list(seasons: Union[List[int], List[str], str]) -> List[int]:
    """Validate and normalize a list of seasons.
    
    Args:
        seasons: List of seasons or comma-separated string
        
    Returns:
        List of validated seasons
        
    Raises:
        ValueError: If any season is invalid
    """
    if isinstance(seasons, str):
        seasons = [s.strip() for s in seasons.split(",")]
    
    validated_seasons = []
    for season in seasons:
        validated_seasons.append(validate_season(season))
    
    # Sort and remove duplicates
    return sorted(list(set(validated_seasons)))


def validate_weeks_list(weeks: Union[List[int], List[str], str]) -> List[int]:
    """Validate and normalize a list of weeks.
    
    Args:
        weeks: List of weeks, comma-separated string, or range string (e.g., "1-17")
        
    Returns:
        List of validated weeks
        
    Raises:
        ValueError: If any week is invalid
    """
    if isinstance(weeks, str):
        if "-" in weeks and "," not in weeks:
            # Handle range format like "1-17"
            try:
                start, end = weeks.split("-", 1)
                start_week = validate_week(start)
                end_week = validate_week(end)
                
                if start_week > end_week:
                    raise ValueError(f"Invalid week range: {weeks}. Start week must be <= end week.")
                
                return list(range(start_week, end_week + 1))
            except ValueError as e:
                if "Invalid week range" in str(e):
                    raise
                raise ValueError(f"Invalid week range format: {weeks}. Use format like '1-17'.")
        else:
            # Handle comma-separated format
            weeks = [w.strip() for w in weeks.split(",")]
    
    validated_weeks = []
    for week in weeks:
        validated_weeks.append(validate_week(week))
    
    # Sort and remove duplicates
    return sorted(list(set(validated_weeks)))


def validate_positions_list(positions: Union[List[str], str]) -> List[Position]:
    """Validate and normalize a list of positions.
    
    Args:
        positions: List of positions or comma-separated string
        
    Returns:
        List of validated positions
        
    Raises:
        ValueError: If any position is invalid
    """
    if isinstance(positions, str):
        positions = [p.strip() for p in positions.split(",")]
    
    validated_positions = []
    for position in positions:
        validated_positions.append(validate_position(position))
    
    # Remove duplicates while preserving order
    seen = set()
    unique_positions = []
    for pos in validated_positions:
        if pos not in seen:
            seen.add(pos)
            unique_positions.append(pos)
    
    return unique_positions


def validate_player_id(player_id: str) -> str:
    """Validate player ID format.
    
    Args:
        player_id: NFL player identifier
        
    Returns:
        Validated player ID
        
    Raises:
        ValueError: If player ID is invalid
    """
    if not isinstance(player_id, str):
        raise ValueError("Player ID must be a string")
    
    player_id = player_id.strip()
    
    if not player_id:
        raise ValueError("Player ID cannot be empty")
    
    if len(player_id) > 50:
        raise ValueError("Player ID too long (max 50 characters)")
    
    return player_id


def validate_team_abbreviation(team: str) -> str:
    """Validate NFL team abbreviation.
    
    Args:
        team: NFL team abbreviation
        
    Returns:
        Validated team abbreviation
        
    Raises:
        ValueError: If team abbreviation is invalid
    """
    if not isinstance(team, str):
        raise ValueError("Team abbreviation must be a string")
    
    team = team.upper().strip()
    
    # List of valid NFL team abbreviations
    valid_teams = {
        "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE", 
        "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC", 
        "LV", "LAC", "LAR", "MIA", "MIN", "NE", "NO", "NYG", 
        "NYJ", "PHI", "PIT", "SF", "SEA", "TB", "TEN", "WAS"
    }
    
    if team not in valid_teams:
        raise ValueError(
            f"Invalid team abbreviation: {team}. "
            f"Valid teams: {', '.join(sorted(valid_teams))}"
        )
    
    return team


def validate_budget(budget: Union[int, float, str]) -> float:
    """Validate auction budget value.
    
    Args:
        budget: Auction budget amount
        
    Returns:
        Validated budget as float
        
    Raises:
        ValueError: If budget is invalid
    """
    try:
        budget_float = float(budget)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid budget: {budget}. Must be a valid number.")
    
    if budget_float <= 0:
        raise ValueError(f"Budget must be positive. Got: {budget_float}")
    
    if budget_float > 10000:
        raise ValueError(f"Budget seems too high: {budget_float}. Maximum allowed: 10000")
    
    return budget_float


def validate_games_played(games: Union[int, str]) -> int:
    """Validate games played count.
    
    Args:
        games: Number of games played
        
    Returns:
        Validated games count
        
    Raises:
        ValueError: If games count is invalid
    """
    try:
        games_int = int(games)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid games count: {games}. Must be a valid integer.")
    
    if games_int < 0:
        raise ValueError(f"Games played cannot be negative. Got: {games_int}")
    
    if games_int > 17:
        raise ValueError(f"Games played cannot exceed 17 in a season. Got: {games_int}")
    
    return games_int