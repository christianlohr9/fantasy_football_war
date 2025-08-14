"""Global settings and configuration for Fantasy WAR system."""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CacheSettings(BaseModel):
    """Cache configuration settings."""
    
    enabled: bool = True
    ttl_days: int = 7  # Time to live for cached data
    max_size_gb: float = 2.0  # Maximum cache size in GB
    directory: Path = Path("data/cache")


class DataSettings(BaseModel):
    """Data loading and processing settings."""
    
    start_year: int = 2014  # NFL's "new era" start
    end_year: Optional[int] = None  # Current year if None
    use_nfl_data_py: bool = True
    use_rpy2_fallback: bool = True
    parallel_jobs: int = -1  # Use all available cores


class LoggingSettings(BaseModel):
    """Logging configuration."""
    
    level: str = "INFO"
    format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name}:{function}:{line} - {message}"
    rotation: str = "100 MB"
    retention: str = "30 days"


class Settings(BaseSettings):
    """Main application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="FANTASY_WAR_",
        case_sensitive=False,
    )
    
    # Application settings
    app_name: str = "Fantasy WAR Calculator"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # Component settings
    cache: CacheSettings = Field(default_factory=CacheSettings)
    data: DataSettings = Field(default_factory=DataSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    
    # R integration settings
    r_home: Optional[str] = None  # Path to R installation
    r_libs: Optional[str] = None  # Path to R library directory
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Create cache directory if it doesn't exist
        self.cache.directory.mkdir(parents=True, exist_ok=True)
        
        # Set end_year to current year if not specified
        if self.data.end_year is None:
            from datetime import datetime
            self.data.end_year = datetime.now().year


# Global settings instance
settings = Settings()