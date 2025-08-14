"""NFL data loading from various sources."""

import warnings
from typing import List, Optional, Union, Dict, Any
from datetime import datetime, timedelta

import polars as pl
import numpy as np
from loguru import logger

# NFL data loading
try:
    import nfl_data_py as nfl
    NFL_DATA_PY_AVAILABLE = True
except ImportError:
    NFL_DATA_PY_AVAILABLE = False
    logger.warning("nfl_data_py not available, will use rpy2 fallback")

# R integration
try:
    import rpy2.robjects as robjects
    from rpy2.robjects import pandas2ri, numpy2ri
    from rpy2.robjects.packages import importr
    from rpy2.robjects import conversion
    RPI2_AVAILABLE = True
    
    # Create conversion context that includes pandas and numpy converters
    def get_r_conversion_context():
        """Get R conversion context with pandas and numpy converters."""
        # Use the localconverter for temporary conversion context
        from rpy2.robjects.conversion import localconverter
        return localconverter(pandas2ri.converter + numpy2ri.converter)
    
except (ImportError, ValueError, Exception) as e:
    RPI2_AVAILABLE = False
    robjects = None
    pandas2ri = None
    numpy2ri = None
    importr = None
    get_r_conversion_context = None
    logger.warning(f"rpy2 not available, R integration disabled: {e}")

from fantasy_war.config.settings import settings
from fantasy_war.data.cache import cache_manager


class NFLDataLoader:
    """Loads NFL data from multiple sources with caching."""
    
    def __init__(self):
        """Initialize NFL data loader."""
        self.use_nfl_data_py = settings.data.use_nfl_data_py and NFL_DATA_PY_AVAILABLE
        self.use_rpy2_fallback = settings.data.use_rpy2_fallback and RPI2_AVAILABLE
        
        if not self.use_nfl_data_py and not self.use_rpy2_fallback:
            raise RuntimeError("No NFL data sources available. Install R/rpy2 or nfl_data_py.")
        
        # Log priority: R is preferred for comprehensive data
        if self.use_rpy2_fallback:
            logger.info(f"NFL data loader initialized: R/rpy2=✅ (primary), nfl_data_py={self.use_nfl_data_py} (fallback)")
        else:
            logger.info(f"NFL data loader initialized: nfl_data_py={self.use_nfl_data_py} (limited IDP), R/rpy2=❌")
        
        # Initialize R packages if using rpy2
        if self.use_rpy2_fallback:
            self._init_r_packages()
    
    def _init_r_packages(self):
        """Initialize required R packages."""
        try:
            self.nflfastr = importr('nflfastR')
            self.nflreadr = importr('nflreadr')
            self.tidyverse = importr('tidyverse')
            logger.info("R packages loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load R packages: {e}")
            self.use_rpy2_fallback = False
    
    def load_pbp_data(self, years: Union[int, List[int]]) -> pl.DataFrame:
        """Load play-by-play data for specified years.
        
        Args:
            years: Year or list of years to load
            
        Returns:
            Polars DataFrame with play-by-play data
        """
        if isinstance(years, int):
            years = [years]
        
        # Try cache first
        cache_key = f"pbp_data_{min(years)}_{max(years)}"
        cached_data = cache_manager.get(cache_key)
        
        if cached_data is not None:
            logger.info(f"Loaded PBP data from cache for years {years}")
            return pl.DataFrame(cached_data)
        
        logger.info(f"Loading PBP data for years {years}")
        
        if self.use_nfl_data_py:
            try:
                df = self._load_pbp_nfl_data_py(years)
            except Exception as e:
                logger.warning(f"nfl_data_py failed: {e}, trying R fallback")
                if self.use_rpy2_fallback:
                    df = self._load_pbp_r(years)
                else:
                    raise
        else:
            df = self._load_pbp_r(years)
        
        # Cache the result
        cache_manager.set(cache_key, df.to_pandas(), timedelta(days=7))
        
        logger.info(f"Loaded {len(df)} plays from {len(years)} seasons")
        return df
    
    def _load_pbp_nfl_data_py(self, years: List[int]) -> pl.DataFrame:
        """Load PBP data using nfl_data_py."""
        data_list = []
        successful_years = []
        
        for year in years:
            logger.debug(f"Loading PBP data for {year}")
            try:
                year_data = nfl.import_pbp_data([year])
                if not year_data.empty:
                    data_list.append(year_data)
                    successful_years.append(year)
                    logger.info(f"Successfully loaded {len(year_data)} plays for {year}")
                else:
                    logger.warning(f"No data available for year {year}")
            except Exception as e:
                logger.warning(f"Failed to load data for year {year}: {e}")
                # Continue with other years if available
                continue
        
        if not data_list:
            raise RuntimeError(f"No data could be loaded for any of the requested years: {years}")
        
        if len(successful_years) < len(years):
            missing_years = set(years) - set(successful_years)
            logger.warning(f"Data not available for years: {missing_years}. Proceeding with: {successful_years}")
        
        # Combine all years
        combined_df = pl.concat([pl.from_pandas(df) for df in data_list])
        return combined_df
    
    def _load_pbp_r(self, years: List[int]) -> pl.DataFrame:
        """Load PBP data using R nflfastR."""
        if not self.use_rpy2_fallback:
            raise RuntimeError("R integration not available")
        
        # Create R vector of years
        r_years = robjects.IntVector(years)
        
        # Load data using nflfastR
        pbp_data = self.nflfastr.load_pbp(r_years)
        
        # Convert to pandas then polars using context
        with get_r_conversion_context():
            pandas_df = robjects.conversion.rpy2py(pbp_data)
        return pl.from_pandas(pandas_df)
    
    def load_player_stats(self, years: Union[int, List[int]], weekly: bool = True, include_idp: bool = True) -> pl.DataFrame:
        """Load player statistics.
        
        Args:
            years: Year or list of years to load
            weekly: If True, load weekly stats; if False, season totals
            include_idp: If True, attempt to load IDP data via R fallback
            
        Returns:
            Polars DataFrame with player statistics
        """
        if isinstance(years, int):
            years = [years]
        
        stat_type = "weekly" if weekly else "season"
        idp_suffix = "_with_idp" if include_idp else ""
        cache_key = f"player_stats_{stat_type}{idp_suffix}_{min(years)}_{max(years)}"
        cached_data = cache_manager.get(cache_key)
        
        if cached_data is not None:
            logger.info(f"Loaded {stat_type} player stats from cache for years {years}")
            return pl.DataFrame(cached_data)
        
        logger.info(f"Loading {stat_type} player stats for years {years} (IDP: {include_idp})")
        
        # Load PBP data first
        pbp_data = self.load_pbp_data(years)
        
        # Always prefer R over nfl_data_py for better defensive coverage
        if self.use_rpy2_fallback:
            logger.info("Using R nflfastR for comprehensive player data (including IDP)")
            try:
                df = self._calculate_stats_r(pbp_data, weekly)
                logger.info(f"Successfully loaded stats via R nflfastR: {len(df)} records")
            except Exception as e:
                logger.warning(f"R stats calculation failed: {e}, falling back to nfl_data_py")
                if self.use_nfl_data_py:
                    df = self._calculate_stats_nfl_data_py(pbp_data, weekly)
                    if include_idp:
                        logger.warning("Using nfl_data_py fallback - IDP coverage will be very limited!")
                else:
                    raise
        elif self.use_nfl_data_py:
            try:
                df = self._calculate_stats_nfl_data_py(pbp_data, weekly)
                if include_idp:
                    logger.warning("nfl_data_py has extremely limited IDP coverage. Install R/rpy2 for complete IDP data!")
            except Exception as e:
                logger.warning(f"nfl_data_py stats calculation failed: {e}")
                raise  # No fallback available
        else:
            raise RuntimeError("No data sources available - install either R/rpy2 or nfl_data_py")
        
        # Cache the result
        cache_manager.set(cache_key, df.to_pandas(), timedelta(days=7))
        
        logger.info(f"Calculated stats for {len(df)} player-weeks")
        return df
    
    def _calculate_stats_nfl_data_py(self, pbp_data: pl.DataFrame, weekly: bool) -> pl.DataFrame:
        """Load player stats using nfl_data_py import functions."""
        # nfl_data_py doesn't have calculate functions - use import functions instead
        years = pbp_data.select("season").unique().to_pandas()["season"].tolist()
        
        if weekly:
            # Import weekly stats directly for each year
            data_list = []
            for year in years:
                try:
                    logger.debug(f"Loading weekly stats for {year}")
                    year_data = nfl.import_weekly_data([year])
                    if not year_data.empty:
                        data_list.append(year_data)
                        logger.info(f"Successfully loaded weekly stats for {year}: {len(year_data)} player-weeks")
                except Exception as e:
                    logger.warning(f"Failed to load weekly stats for {year}: {e}")
                    continue
            
            if not data_list:
                raise RuntimeError(f"No weekly stats could be loaded for years: {years}")
                
            combined_df = pl.concat([pl.from_pandas(df) for df in data_list])
            return combined_df
        else:
            # Import seasonal stats directly for each year  
            data_list = []
            for year in years:
                try:
                    logger.debug(f"Loading seasonal stats for {year}")
                    year_data = nfl.import_seasonal_data([year], 'REG')
                    if not year_data.empty:
                        data_list.append(year_data)
                        logger.info(f"Successfully loaded seasonal stats for {year}: {len(year_data)} players")
                except Exception as e:
                    logger.warning(f"Failed to load seasonal stats for {year}: {e}")
                    continue
            
            if not data_list:
                raise RuntimeError(f"No seasonal stats could be loaded for years: {years}")
                
            combined_df = pl.concat([pl.from_pandas(df) for df in data_list])
            return combined_df
    
    def _map_new_defensive_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Map new nflfastR column names to expected defensive column names."""
        column_mapping = {
            # Defensive stats mapping from new calculate_stats to expected names
            'def_tackles_solo': 'tackles',
            'def_tackle_assists': 'assists', 
            'def_tackles_for_loss': 'tackles_for_loss',
            'def_sacks': 'sacks_def',
            'def_qb_hits': 'qb_hits',
            'def_pass_defended': 'passes_defended',
            'def_interceptions': 'interceptions_def',
            'def_fumbles_forced': 'forced_fumbles',
            'def_fumbles': 'fumble_recoveries',
            'def_safeties': 'safeties',
            'def_tds': 'defensive_tds',
        }
        
        # Rename columns that exist
        for new_col, old_col in column_mapping.items():
            if new_col in df.columns:
                df = df.rename({new_col: old_col})
                logger.debug(f"Mapped column {new_col} -> {old_col}")
        
        return df
    
    def _calculate_stats_r(self, pbp_data: pl.DataFrame, weekly: bool) -> pl.DataFrame:
        """Calculate player stats using R nflfastR."""
        if not self.use_rpy2_fallback:
            raise RuntimeError("R integration not available")
        
        # Extract years from pbp_data for new calculate_stats function
        years = sorted(pbp_data['season'].unique().to_list())
        
        # Use the new comprehensive calculate_stats function directly
        # This replaces the old calculate_player_stats approach completely
        weekly_str = "week" if weekly else "season"
        r_years = robjects.IntVector(years)
        
        with get_r_conversion_context():
            all_stats = self.nflfastr.calculate_stats(r_years, weekly_str, "player")
            # Handle the R output conversion properly
            if hasattr(all_stats, 'to_pandas'):
                # If it's an R DataFrame, convert to pandas first
                all_stats_df = pl.from_pandas(all_stats.to_pandas())
            else:
                # Direct conversion from R object
                import pandas as pd
                all_stats_df = pl.from_pandas(pd.DataFrame(all_stats))
        
        logger.info(f"Successfully loaded comprehensive player stats from R nflfastR: {len(all_stats_df)} rows")
        
        # Clean up data - remove rows with null critical values
        all_stats_df = all_stats_df.filter(
            (pl.col("player_id").is_not_null()) &
            (pl.col("player_name").is_not_null()) & 
            (pl.col("position").is_not_null())
        )
        logger.info(f"After cleaning null values: {len(all_stats_df)} rows")
        
        # Map new column names to expected schema for defensive stats
        all_stats_df = self._map_new_defensive_columns(all_stats_df)
        
        # The new function includes ALL players (offensive, defensive, kicking, punting)
        # Apply position normalization for defensive positions
        all_stats_df = all_stats_df.with_columns([
            # Map defensive positions to standard IDP positions
            pl.when(pl.col("position").is_in(["DT", "NT"]))
              .then(pl.lit("DT"))
            .when(pl.col("position").is_in(["DE", "EDGE"]))
              .then(pl.lit("DE"))
            .when(pl.col("position").is_in(["OLB"]))
              .then(pl.lit("DE"))  # OLB often acts as pass rusher
            .when(pl.col("position").is_in(["ILB", "MLB", "LB"]))
              .then(pl.lit("LB"))
            .when(pl.col("position").is_in(["CB", "DB"]))
              .then(pl.lit("CB"))
            .when(pl.col("position").is_in(["S", "SS", "FS", "SAF"]))
              .then(pl.lit("S"))
            .when(pl.col("position") == "K")
              .then(pl.lit("PK"))
            .otherwise(pl.col("position"))
            .alias("position")
        ])
        
        logger.info(f"Position normalization complete. Positions found: {sorted(all_stats_df['position'].unique().to_list())}")
        return all_stats_df
    
    def load_ff_opportunity(self, years: Union[int, List[int]], stat_type: str = "weekly") -> pl.DataFrame:
        """Load fantasy football opportunity data.
        
        Args:
            years: Year or list of years to load
            stat_type: "weekly" or "seasonal"
            
        Returns:
            Polars DataFrame with opportunity data including expected points
        """
        if isinstance(years, int):
            years = [years]
        
        cache_key = f"ff_opportunity_{stat_type}_{min(years)}_{max(years)}"
        cached_data = cache_manager.get(cache_key)
        
        if cached_data is not None:
            logger.info(f"Loaded FF opportunity data from cache for years {years}")
            return pl.DataFrame(cached_data)
        
        logger.info(f"Loading FF opportunity data for years {years}")
        
        if self.use_rpy2_fallback:
            # Use R nflreadr for opportunity data
            r_years = robjects.IntVector(years)
            opportunity_data = self.nflreadr.load_ff_opportunity(r_years, stat_type=stat_type)
            df = pl.from_pandas(pandas2ri.rpy2py(opportunity_data))
        else:
            # Fallback: calculate basic opportunity metrics from PBP
            logger.warning("Using basic opportunity calculation (R nflreadr not available)")
            df = self._calculate_basic_opportunity(years, stat_type)
        
        # Cache the result
        cache_manager.set(cache_key, df.to_pandas(), timedelta(days=7))
        
        logger.info(f"Loaded opportunity data for {len(df)} player entries")
        return df
    
    def _calculate_basic_opportunity(self, years: List[int], stat_type: str) -> pl.DataFrame:
        """Calculate basic opportunity metrics from PBP data."""
        pbp_data = self.load_pbp_data(years)
        
        # Basic opportunity calculations (simplified version)
        # This is a fallback when nflreadr is not available
        
        opportunity_cols = [
            "season", "week", "player_id", "position",
            "targets", "carries", "pass_attempts",
            # Add expected point calculations here based on EPA
        ]
        
        # Filter to relevant plays and calculate basic metrics
        # This is a simplified version - the R version has more sophisticated EPA calculations
        
        opportunity_data = (
            pbp_data
            .filter(pl.col("play_type").is_in(["pass", "run"]))
            .group_by(["season", "week", "player_id", "position"])
            .agg([
                pl.count("play_id").alias("plays"),
                pl.sum("epa").alias("total_epa"),
                pl.mean("epa").alias("avg_epa"),
            ])
        )
        
        return opportunity_data
    
    def load_roster_data(self, years: Union[int, List[int]]) -> pl.DataFrame:
        """Load NFL roster data for player identification.
        
        Args:
            years: Year or list of years to load
            
        Returns:
            Polars DataFrame with roster/player information
        """
        if isinstance(years, int):
            years = [years]
        
        cache_key = f"roster_data_{min(years)}_{max(years)}"
        cached_data = cache_manager.get(cache_key)
        
        if cached_data is not None:
            logger.info(f"Loaded roster data from cache for years {years}")
            return pl.DataFrame(cached_data)
        
        logger.info(f"Loading roster data for years {years}")
        
        if self.use_nfl_data_py:
            try:
                data_list = []
                for year in years:
                    roster_data = nfl.import_rosters([year])
                    data_list.append(roster_data)
                combined_df = pl.concat([pl.from_pandas(df) for df in data_list])
            except Exception as e:
                logger.warning(f"nfl_data_py roster loading failed: {e}")
                if self.use_rpy2_fallback:
                    combined_df = self._load_roster_r(years)
                else:
                    raise
        else:
            combined_df = self._load_roster_r(years)
        
        # Cache the result
        cache_manager.set(cache_key, combined_df.to_pandas(), timedelta(days=30))  # Cache longer for roster data
        
        logger.info(f"Loaded roster data for {len(combined_df)} player-seasons")
        return combined_df
    
    def _load_roster_r(self, years: List[int]) -> pl.DataFrame:
        """Load roster data using R nflfastR."""
        if not self.use_rpy2_fallback:
            raise RuntimeError("R integration not available")
        
        data_list = []
        for year in years:
            roster_data = self.nflfastr.fast_scraper_roster(year)
            with get_r_conversion_context():
                pandas_df = robjects.conversion.rpy2py(roster_data)
            data_list.append(pl.from_pandas(pandas_df))
        
        return pl.concat(data_list)
    
    def load_idp_stats(self, years: Union[int, List[int]], weekly: bool = True) -> pl.DataFrame:
        """Load Individual Defensive Player (IDP) statistics specifically.
        
        Args:
            years: Year or list of years to load
            weekly: If True, load weekly stats; if False, season totals
            
        Returns:
            Polars DataFrame with IDP statistics (tackles, sacks, INTs, etc.)
        """
        if isinstance(years, int):
            years = [years]
        
        stat_type = "weekly" if weekly else "season"
        cache_key = f"idp_stats_{stat_type}_{min(years)}_{max(years)}"
        cached_data = cache_manager.get(cache_key)
        
        if cached_data is not None:
            logger.info(f"Loaded IDP stats from cache for years {years}")
            return pl.DataFrame(cached_data)
        
        logger.info(f"Loading IDP stats for years {years}")
        
        if not self.use_rpy2_fallback:
            logger.warning("R/rpy2 not available. IDP data will be limited. Install R and rpy2 for comprehensive IDP coverage.")
            # Return basic defensive data from nfl_data_py if available
            return self.load_player_stats(years, weekly, include_idp=False).filter(
                pl.col("position").is_in(["CB", "S", "SS", "FS", "LB", "DE", "DT"])
            )
        
        try:
            # Use the new comprehensive calculate_stats function for all player data
            weekly_str = "week" if weekly else "season"
            r_years = robjects.IntVector(years)
            with get_r_conversion_context():
                all_stats = self.nflfastr.calculate_stats(r_years, weekly_str, "player")
                # Handle the R output conversion properly
                if hasattr(all_stats, 'to_pandas'):
                    # If it's an R DataFrame, convert to pandas first
                    idp_df = pl.from_pandas(all_stats.to_pandas())
                else:
                    # Direct conversion from R object
                    import pandas as pd
                    idp_df = pl.from_pandas(pd.DataFrame(all_stats))
            
            # Clean up data - remove rows with null critical values
            idp_df = idp_df.filter(
                (pl.col("player_id").is_not_null()) &
                (pl.col("player_name").is_not_null()) & 
                (pl.col("position").is_not_null())
            )
            logger.info(f"IDP data after cleaning null values: {len(idp_df)} rows")
            
            # Map new column names to expected defensive column names
            idp_df = self._map_new_defensive_columns(idp_df)
            
            # Enhance with detailed IDP position mapping and stats  
            idp_df = idp_df.with_columns([
                # Standardize positions for IDP
                pl.when(pl.col("position").is_in(["DT", "NT"]))
                  .then(pl.lit("DT"))
                .when(pl.col("position").is_in(["DE", "EDGE"]))
                  .then(pl.lit("DE"))
                .when(pl.col("position").is_in(["OLB"]))
                  .then(pl.lit("DE"))  # Most OLBs are pass rushers
                .when(pl.col("position").is_in(["ILB", "MLB", "LB"]))
                  .then(pl.lit("LB"))
                .when(pl.col("position").is_in(["CB", "DB"]))
                  .then(pl.lit("CB"))
                .when(pl.col("position").is_in(["S", "SS", "FS", "SAF"]))
                  .then(pl.lit("S"))
                .otherwise(pl.col("position"))
                .alias("position")
            ])
            
            # Filter to only IDP positions
            idp_df = idp_df.filter(
                pl.col("position").is_in(["DT", "DE", "LB", "CB", "S"])
            )
            
            # Cache the result
            cache_manager.set(cache_key, idp_df.to_pandas(), timedelta(days=7))
            
            logger.info(f"Loaded IDP stats for {len(idp_df)} defensive player entries")
            return idp_df
            
        except Exception as e:
            logger.error(f"Failed to load IDP stats via R: {e}")
            logger.warning("Falling back to limited defensive data from nfl_data_py")
            
            # Fallback to limited data
            basic_stats = self.load_player_stats(years, weekly, include_idp=False)
            return basic_stats.filter(
                pl.col("position").is_in(["CB", "S", "SS", "FS"])
            )