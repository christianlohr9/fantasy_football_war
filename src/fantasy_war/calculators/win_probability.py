"""Win probability calculations for WAR analysis."""

import math
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy import stats
from loguru import logger

from fantasy_war.config.leagues import LeagueConfig


class WinProbabilityCalculator:
    """Calculates win probabilities using normal distribution (replicating R's pnorm)."""
    
    def __init__(self, league_config: LeagueConfig):
        """Initialize win probability calculator.
        
        Args:
            league_config: League configuration
        """
        self.league_config = league_config
        self.distribution_method = "normal"  # Can be extended for other methods
        
        logger.info("Win probability calculator initialized")
    
    def calculate_win_probability(
        self,
        player_score: float,
        team_average_score: float,
        team_score_std: float
    ) -> float:
        """Calculate win probability for a player's expected team score.
        
        This replicates the pnorm function from the R script:
        pnorm(expected_team_score, mean=team_avg_score, sd=team_score_std)
        
        Args:
            player_score: Player's contribution to team score
            team_average_score: Average team score in the league
            team_score_std: Standard deviation of team scores
            
        Returns:
            Win probability (0.0 to 1.0)
        """
        if team_score_std <= 0:
            logger.warning("Team score standard deviation is zero or negative, using default")
            team_score_std = 1.0
        
        # Calculate expected team score with this player
        # The original R script adds/subtracts individual player performance from team average
        expected_team_score = player_score
        
        # Use scipy.stats.norm.cdf to replicate R's pnorm
        # pnorm gives the cumulative probability (CDF) of the normal distribution
        win_prob = stats.norm.cdf(
            expected_team_score,
            loc=team_average_score,
            scale=team_score_std
        )
        
        # Ensure win probability is within valid bounds
        win_prob = max(0.0, min(1.0, win_prob))
        
        return win_prob
    
    def calculate_team_expected_score(
        self,
        player_fantasy_points: float,
        position_average: float,
        team_baseline_score: float
    ) -> float:
        """Calculate expected team score with a specific player.
        
        This follows the R script logic of:
        exp_team_score = (player_points - position_avg) + team_baseline
        
        Args:
            player_fantasy_points: Player's fantasy points  
            position_average: Average fantasy points for the position
            team_baseline_score: Baseline team score
            
        Returns:
            Expected team score with this player
        """
        player_contribution = player_fantasy_points - position_average
        expected_score = team_baseline_score + player_contribution
        
        return expected_score
    
    def calculate_win_probability_detailed(
        self,
        player_fantasy_points: float,
        position_average: float,
        team_baseline_score: float,
        opponent_average_score: float,
        league_score_std: float
    ) -> Dict[str, float]:
        """Calculate detailed win probability with intermediate values.
        
        Args:
            player_fantasy_points: Player's fantasy points
            position_average: Average for the player's position
            team_baseline_score: Team's baseline score
            opponent_average_score: Average opponent score
            league_score_std: League-wide score standard deviation
            
        Returns:
            Dictionary with detailed probability calculations
        """
        # Calculate expected team score
        expected_team_score = self.calculate_team_expected_score(
            player_fantasy_points, position_average, team_baseline_score
        )
        
        # Calculate win probability against average opponent
        win_prob = self.calculate_win_probability(
            expected_team_score, opponent_average_score, league_score_std
        )
        
        # Calculate additional metrics
        expected_margin = expected_team_score - opponent_average_score
        margin_z_score = expected_margin / league_score_std if league_score_std > 0 else 0.0
        
        return {
            'expected_team_score': expected_team_score,
            'expected_margin': expected_margin,
            'win_probability': win_prob,
            'z_score': margin_z_score,
            'player_contribution': player_fantasy_points - position_average,
        }
    
    def calculate_strength_of_schedule_adjustment(
        self,
        opponent_scores: List[float],
        league_average_score: float
    ) -> float:
        """Calculate strength of schedule adjustment factor.
        
        This can be used to adjust win probabilities based on
        the difficulty of opponents faced.
        
        Args:
            opponent_scores: List of opponent team scores faced
            league_average_score: League average team score
            
        Returns:
            SOS adjustment factor (1.0 = average, >1.0 = harder schedule)
        """
        if not opponent_scores:
            return 1.0
        
        avg_opponent_score = np.mean(opponent_scores)
        sos_adjustment = avg_opponent_score / league_average_score
        
        # Cap adjustment to reasonable bounds
        sos_adjustment = max(0.5, min(2.0, sos_adjustment))
        
        return sos_adjustment
    
    def simulate_season_outcomes(
        self,
        player_win_probs: List[float],
        num_simulations: int = 10000
    ) -> Dict[str, float]:
        """Simulate season outcomes based on weekly win probabilities.
        
        This provides a more sophisticated analysis than simple
        expected wins by accounting for variance in outcomes.
        
        Args:
            player_win_probs: List of win probabilities for each game
            num_simulations: Number of Monte Carlo simulations
            
        Returns:
            Dictionary with simulation results
        """
        if not player_win_probs:
            return {'expected_wins': 0.0, 'win_probability_distribution': []}
        
        # Run Monte Carlo simulations
        season_wins = []
        
        for _ in range(num_simulations):
            # Simulate each game as a Bernoulli trial
            games_won = sum(1 for wp in player_win_probs if np.random.random() < wp)
            season_wins.append(games_won)
        
        season_wins = np.array(season_wins)
        
        # Calculate statistics
        results = {
            'expected_wins': np.mean(season_wins),
            'median_wins': np.median(season_wins),
            'std_wins': np.std(season_wins),
            'min_wins': np.min(season_wins),
            'max_wins': np.max(season_wins),
            'win_distribution': np.bincount(season_wins, minlength=len(player_win_probs)+1),
        }
        
        # Calculate probability of different win totals
        total_games = len(player_win_probs)
        win_probabilities = results['win_distribution'] / num_simulations
        
        results['win_probability_distribution'] = [
            {'wins': i, 'probability': prob} 
            for i, prob in enumerate(win_probabilities)
        ]
        
        # Playoff probability (assuming top 50% make playoffs)
        playoff_threshold = total_games * 0.6  # 60% win rate threshold
        playoff_prob = np.sum(season_wins >= playoff_threshold) / num_simulations
        results['playoff_probability'] = playoff_prob
        
        return results
    
    def calculate_value_over_replacement_curve(
        self,
        fantasy_points_range: Tuple[float, float],
        replacement_level_points: float,
        team_context: Dict[str, float],
        num_points: int = 100
    ) -> List[Dict[str, float]]:
        """Calculate WAR curve showing value over replacement level.
        
        This creates a curve showing how WAR changes with fantasy point production,
        useful for understanding marginal value and draft strategy.
        
        Args:
            fantasy_points_range: (min_points, max_points) for the curve
            replacement_level_points: Fantasy points of replacement level player
            team_context: Dictionary with team_avg_score and team_score_std
            num_points: Number of points to calculate on the curve
            
        Returns:
            List of dictionaries with fantasy_points, win_prob, and war values
        """
        min_points, max_points = fantasy_points_range
        
        if min_points >= max_points:
            logger.warning("Invalid fantasy points range")
            return []
        
        # Create fantasy points range
        point_values = np.linspace(min_points, max_points, num_points)
        
        # Calculate replacement level win probability
        replacement_win_prob = self.calculate_win_probability(
            replacement_level_points,
            team_context['team_avg_score'],
            team_context['team_score_std']
        )
        
        # Calculate curve
        curve_points = []
        
        for points in point_values:
            win_prob = self.calculate_win_probability(
                points,
                team_context['team_avg_score'],
                team_context['team_score_std']
            )
            
            # Assume 17 games for WAR calculation
            games = 17
            expected_wins = win_prob * games
            replacement_wins = replacement_win_prob * games
            war = expected_wins - replacement_wins
            
            curve_points.append({
                'fantasy_points': points,
                'win_probability': win_prob,
                'expected_wins': expected_wins,
                'war': war,
                'marginal_war': war - (curve_points[-1]['war'] if curve_points else 0),
            })
        
        return curve_points
    
    def estimate_optimal_roster_construction(
        self,
        position_war_values: Dict[str, List[float]],
        budget_constraint: float
    ) -> Dict[str, int]:
        """Estimate optimal roster construction given WAR values and budget.
        
        This is a simplified optimization that could be extended with
        more sophisticated algorithms.
        
        Args:
            position_war_values: Dictionary mapping positions to lists of WAR values
            budget_constraint: Total budget/value available
            
        Returns:
            Dictionary with recommended number of players per position
        """
        # This is a placeholder for more sophisticated roster optimization
        # In practice, this would use linear programming or other optimization techniques
        
        recommendations = {}
        
        for position, war_values in position_war_values.items():
            if not war_values:
                recommendations[position] = 0
                continue
            
            # Simple heuristic: recommend based on top player value
            max_war = max(war_values)
            
            if max_war > 2.0:
                recommendations[position] = 3  # High value position
            elif max_war > 1.0:
                recommendations[position] = 2  # Medium value position
            else:
                recommendations[position] = 1  # Low value position
        
        return recommendations