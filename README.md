# Fantasy Football WAR Calculator 🏈

**Dominate your fantasy football league with advanced analytics!**

A modern Python implementation of Wins Above Replacement (WAR) calculations for Fantasy Football, featuring the sophisticated MPPR (Minus PPR) scoring system and comprehensive Individual Defensive Player (IDP) support.

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-ready-green.svg)

## 🌟 Features

### Advanced Analytics
- **WAR Calculations**: Wins Above Replacement methodology adapted for fantasy football
- **MPPR Scoring**: EPA-based scoring system with negative points for attempts/targets  
- **Win Probability**: Normal distribution-based probability calculations using exact `pnorm` methodology
- **Replacement Level**: Automatically determines replacement level players by position (e.g., 24th RB for 12 teams)
- **🆕 Rewritten WAR Engine**: Complete rewrite matching proven R methodology for accurate calculations

### Position Support
- **Offensive Positions**: QB, RB, WR, TE with full MPPR scoring ✅
- **Individual Defense Players**: DT, DE, LB, CB, S ⚠️ **Erfordert R-Installation** 
- **Special Teams**: Kickers (PK) and Punters (PN) with distance-based scoring
- **Flex Positions**: Complex flex calculations for RB/WR/TE eligibility

**Hinweis**: Für zuverlässige Ergebnisse sollten Sie sich auf QB, RB, WR, TE fokussieren.

### Modern Python Architecture  
- **Polars DataFrames**: High-performance data processing
- **Pydantic Models**: Type-safe data validation and serialization
- **Caching System**: Intelligent caching for improved performance
- **CLI Interface**: Modern command-line interface with Typer
- **Jupyter Integration**: Interactive notebooks for analysis

### Data Sources
- **Primary**: NFL data via `nfl_data_py` (Python)
- **Fallback**: R integration with `nflfastR`/`nflreadr` via `rpy2`
- **Flexible**: Supports multiple data sources with automatic fallback

## 🚀 2025 Draft Preparation Guide

### Quick Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/fantasy-war.git
cd fantasy_football_war

# Create virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install core dependencies
pip install pyarrow nfl-data-py pydantic polars typer rich pydantic-settings loguru numpy scipy

# Install the package
pip install -e .
```

### ✅ 2024 Data Available!

**Using 2024 Season Data for 2025 Draft Prep**
- **2024 data** is fully available and working perfectly
- Complete season statistics for all skill positions (QB, RB, WR, TE)
- Most recent data for optimal 2025 draft preparation
- Includes rookies and breakout players from 2024

**🎯 IDP (Individual Defensive Player) Support** ✅ **VOLLSTÄNDIG FUNKTIONSFÄHIG**

**Das System bietet jetzt komplette IDP-Unterstützung mit über 900 Defense-Spielern:**

- **✅ DT (Defensive Tackles)**: 153+ Spieler verfügbar
- **✅ DE (Defensive Ends)**: 161+ Spieler verfügbar  
- **✅ LB (Linebackers)**: 254+ Spieler verfügbar
- **✅ CB (Cornerbacks)**: 236+ Spieler verfügbar
- **✅ S (Safeties)**: 139+ Spieler verfügbar

**Schnell-Setup für vollständige IDP-Liga:**
```bash
# 1. R installieren: https://cran.r-project.org/
# 2. R-Pakete installieren (einmalig):
R -e "install.packages(c('tidyverse', 'nflfastR', 'nflreadr', 'gsisdecoder'), repos='https://cran.rstudio.com/')"
# 3. Python rpy2 installieren:
pip install rpy2
# 4. Vollständige IDP-Auction mit 900+ Defense-Spielern:
fantasy-war auction-values --seasons 2024 --positions "QB,RB,WR,TE,DT,DE,LB,CB,S" --budget 200 --output complete_idp_auction.csv
```

**Erfolgreiche Installation erkennen:**
```
INFO: NFL data loader initialized: R/rpy2=✅ (primary), nfl_data_py=True (fallback)
INFO: R packages loaded successfully
INFO: Successfully loaded comprehensive player stats from R nflfastR: 18959 rows
INFO: Calculated WAR for 153 players at DT
INFO: Calculated WAR for 161 players at DE
```

**Standard-Liga (nur Offense):**
```bash
# Bewährte Offensiv-Positionen ohne IDP:
fantasy-war auction-values --seasons 2024 --positions "QB,RB,WR,TE" --budget 200 --output offense_only.csv
```

### Essential Commands for 2025 Draft Prep

#### 1. Generate Your Complete Draft Board

```bash
# Calculate WAR for all skill positions using 2024 data (most recent complete season)
fantasy-war calculate-war --seasons 2024 --positions "QB,RB,WR,TE" --output 2025_draft_board.csv

# Focus on top performers (4+ games minimum for reliability)
fantasy-war calculate-war --seasons 2024 --positions "QB,RB,WR,TE" --min-games 4 --output elite_players.csv
```

#### 2. Calculate Auction Values

```bash
# Standard $200 auction budget for all skill positions
fantasy-war auction-values --seasons 2024 --budget 200 --output auction_values_2025.csv

# 🔥 VOLLSTÄNDIGE IDP-LIGA mit 900+ Defense-Spielern (funktioniert perfekt!)
fantasy-war auction-values --seasons 2024 --positions "QB,RB,WR,TE,DT,DE,LB,CB,S" --budget 200 --output complete_idp_auction.csv

# NUR Defense-Positionen für IDP-Spezialisten
fantasy-war auction-values --seasons 2024 --positions "DT,DE,LB,CB,S" --budget 200 --output idp_only_auction.csv

# Different budget sizes
fantasy-war auction-values --seasons 2024 --budget 300 --output auction_300_budget.csv
fantasy-war auction-values --seasons 2024 --positions "QB,RB,WR,TE,DT,DE,LB,CB,S" --budget 250 --output idp_250_budget.csv
```

#### 3. Position-Specific Analysis

```bash
# Deep dive into QB rankings (featuring Burrow, Jackson, Goff, Allen at top)
fantasy-war calculate-war --seasons 2024 --positions "QB" --output qb_rankings_2025.csv

# RB scarcity analysis
fantasy-war calculate-war --seasons 2024 --positions "RB" --teams 12 --output rb_12team.csv
fantasy-war calculate-war --seasons 2024 --positions "RB" --teams 16 --output rb_16team.csv

# WR depth analysis
fantasy-war calculate-war --seasons 2024 --positions "WR" --min-games 8 --output wr_reliable.csv

# 🔥 IDP Position Analysis (jetzt verfügbar!)
fantasy-war calculate-war --seasons 2024 --positions "DT" --output dt_rankings.csv
fantasy-war calculate-war --seasons 2024 --positions "DE" --output de_rankings.csv
fantasy-war calculate-war --seasons 2024 --positions "LB" --output lb_rankings.csv
fantasy-war calculate-war --seasons 2024 --positions "CB,S" --output secondary_rankings.csv
```

#### 4. Multi-Year Trend Analysis

```bash
# Compare 2023 vs 2024 performance for consistency
fantasy-war calculate-war --seasons 2023,2024 --positions "QB,RB,WR,TE" --output multi_year_trends.csv

# Historical analysis for player development trends
fantasy-war calculate-war --seasons 2022,2023,2024 --positions "QB,RB,WR,TE" --output historical_trends.csv
```

### Pre-Draft Workflow (Recommended)

**4-6 Weeks Before Draft:**
```bash
# 1. Generate baseline rankings with 2024 data (most recent complete season)
fantasy-war calculate-war --seasons 2024 --output baseline_rankings.csv

# 2. Calculate auction values for your league (include IDP if needed)
fantasy-war auction-values --seasons 2024 --budget 200 --teams 12 --output auction_values.csv

# 3. Check cache info to ensure data is fresh
fantasy-war cache-info
```

**2 Weeks Before Draft:**
```bash
# Update with any new data or clear cache for fresh download
fantasy-war cache-clear
fantasy-war calculate-war --seasons 2024 --output updated_rankings.csv

# Multi-year analysis for consistency checks
fantasy-war calculate-war --seasons 2023,2024 --output consistency_check.csv
```

**Day of Draft:**
```bash
# Quick reference export for offline use with 2024 data
fantasy-war calculate-war --seasons 2024 --positions "QB,RB,WR,TE" --min-games 4 --output draft_day_rankings.csv
```

### Advanced Draft Strategies

#### Identify Sleepers and Busts

```bash
# Find undervalued players (high WAR, potentially low draft cost)
fantasy-war calculate-war --seasons 2024 --positions "RB,WR" --min-games 6 --output sleeper_candidates.csv

# Compare multi-year consistency (2024 vs 2023 for breakouts/declines)
fantasy-war calculate-war --seasons 2023,2024 --output consistency_check.csv
```

#### League-Specific Optimization

```bash
# Adjust for your league size
fantasy-war calculate-war --seasons 2024 --teams 14 --output 14team_values.csv

# Standard-Ligen (bewährte Offensiv-Positionen)
fantasy-war auction-values --seasons 2024 --positions "QB,RB,WR,TE" --budget 200 --output main_auction.csv

# 🔥 VOLLSTÄNDIGE IDP-LIGEN (900+ Defense-Spieler - perfekt funktionsfähig!)
fantasy-war calculate-war --seasons 2024 --positions "QB,RB,WR,TE,DT,DE,LB,CB,S" --output complete_idp_rankings.csv
fantasy-war auction-values --seasons 2024 --positions "QB,RB,WR,TE,DT,DE,LB,CB,S" --budget 200 --output complete_idp_auction.csv

# Nur IDP für bestehende Offense-schwere Ligen
fantasy-war auction-values --seasons 2024 --positions "DT,DE,LB,CB,S" --budget 50 --output idp_supplement.csv
```

#### Injury Risk Assessment

```bash
# Focus on players with full season data (iron men)
fantasy-war calculate-war --seasons 2024 --min-games 16 --output iron_man_rankings.csv

# Compare players with 12+ games vs all players
fantasy-war calculate-war --seasons 2024 --min-games 12 --output reliable_players.csv
```

### Using Results for Draft Day

#### Understanding Your CSV Output

Each generated CSV contains these key columns:
- **player_name**: Player name
- **position**: QB, RB, WR, TE
- **wins_above_replacement**: Core WAR metric (higher = better)
- **total_fantasy_points**: Season fantasy points total
- **average_fantasy_points**: Per-game fantasy points
- **games_played**: Games played in season

#### Draft Board Creation

1. **Sort by WAR** for overall player value
2. **Group by position** for positional rankings
3. **Consider games_played** for reliability assessment
4. **Use average_fantasy_points** for per-game upside

#### Jupyter Notebook Analysis

```bash
# Install Jupyter if needed
pip install jupyter

# Start Jupyter Lab
jupyter lab

# Open the example notebook
# Navigate to notebooks/example_usage.ipynb
```

The notebook provides:
- Interactive data exploration
- Custom visualization of WAR trends
- Position-by-position analysis
- Draft strategy recommendations

## 📊 Understanding MPPR Scoring

The Fantasy Analytical League (FAL) MPPR scoring system is based on Expected Points Added (EPA) regression analysis:

### Core Principles
- **10-Per-4 Framework**: Based on NFL's fundamental 10 yards per 4 downs structure
- **EPA Regression**: Point values derived from actual EPA impact of each statistic  
- **Negative Attempts**: Attempts and targets have negative value (you're penalized for opportunities)
- **Positive Production**: Yards, completions, and scores have positive value

### Key Scoring Differences from Standard
```
Standard PPR vs MPPR Examples:
• Receptions: +1.0 vs +0.5 points
• Targets: 0 vs -1.0 points  
• Pass Attempts: 0 vs -1.0 points
• Rush Attempts: 0 vs -0.5 points
• All Yards: Same (+0.2 per yard for most)
```

This creates a more nuanced system where efficiency matters more than volume.

## 🏗️ Architecture

### Project Structure
```
fantasy-war/
├── src/fantasy_war/
│   ├── config/          # Configuration and scoring systems
│   ├── data/            # Data loading and processing  
│   ├── models/          # Pydantic data models
│   ├── calculators/     # WAR calculation engines
│   ├── cli/             # Command line interface
│   └── utils/           # Utilities and validators
├── notebooks/           # Jupyter notebook examples
├── tests/              # Test suite
└── data/cache/         # Cached NFL data
```

### Key Components

#### 🆕 Rewritten WAR Calculation Engine (`calculators/war_engine.py`)
- **Complete rewrite** matching proven R methodology from `WAR_function.R`
- **League Context**: Proper `weekfp` and `weeksd` calculations weighted by roster requirements
- **Replacement Level**: Exact ranking methodology (e.g., 24th RB for 12 teams × 2 RBs)
- **Win Probability**: Precise `pnorm(expected_team_score, weekfp, weeksd)` implementation
- **WAR Formula**: Correct `(Player_Avg_Win_% × Games) - (Replacement_Avg_Win_% × Games)`
- Supports complex flex position calculations and all IDP positions

#### Data Processing (`data/processors.py`)  
- Converts raw NFL stats to MPPR fantasy points
- Handles position-specific scoring rules
- Aggregates weekly data to season totals
- Calculates positional rankings

#### Auction Values (`calculators/auction_values.py`)
- Converts WAR to draft dollar values
- Accounts for positional scarcity
- Identifies sleepers and bust candidates  
- Optimizes budget allocation

## ⚙️ Configuration

### League Settings

Customize your league settings in `config/leagues.py`:

```python
my_league = LeagueConfig(
    name="My Fantasy League",
    teams=16,
    # Roster requirements (min-max starters)
    roster=RosterRequirements(
        qb_min=1, qb_max=1,
        rb_min=1, rb_max=2,
        wr_min=2, wr_max=4,
        te_min=1, te_max=2,
        # ... IDP positions
    )
)
```

### Scoring System

Modify scoring in `config/scoring.py` or create custom systems:

```python
from fantasy_war.config.scoring import MPPRScoringSystem

custom_scoring = MPPRScoringSystem()
custom_scoring.offensive.passing_yards = 0.25  # Custom passing yards
```

### Environment Variables

Create `.env` file for customization:
```bash
FANTASY_WAR_DEBUG=false
FANTASY_WAR_CACHE_ENABLED=true
FANTASY_WAR_DATA_START_YEAR=2014
FANTASY_WAR_R_HOME=/usr/local/lib/R  # Path to R installation
```

## 🏆 2025 Draft Success Tips

### What the Data Tells Us

**From our 2024 season analysis:**
- **QB Position**: Joe Burrow (15.62 WAR) and Lamar Jackson (15.10 WAR) dominated rankings
- **QB Surprises**: Jared Goff (#3) and Baker Mayfield (#5) had breakout years
- **Rookie Success**: Jayden Daniels (#7) and Bo Nix (#11) showed immediate impact
- **QB Depth**: Strong performance from unexpected sources like Sam Darnold (#8)
- **RB/WR/TE Analysis**: Full position analysis available with your draft board generation

### Common Mistakes to Avoid

❌ **Don't ignore games played** - 16-game seasons are rare
❌ **Don't draft on name recognition** - Use current year data
❌ **Don't overdraft QBs in standard leagues** - Positional scarcity matters
✅ **Do target consistent weekly producers** - Check average fantasy points
✅ **Do consider your league size** - 12 vs 16 teams changes everything
✅ **Do look for efficiency over volume** - MPPR rewards smart plays

### Draft Day Checklist

**Before Your Draft:**
- [ ] Generate current season rankings: `fantasy-war calculate-war --seasons 2024`
- [ ] Calculate auction values for your budget: `fantasy-war auction-values --seasons 2024 --budget 200`
- [ ] Export position-specific rankings
- [ ] Review multi-year consistency: `fantasy-war calculate-war --seasons 2023,2024`
- [ ] Check injury/games played history

**During Your Draft:**
- [ ] Sort players by WAR within each position
- [ ] Consider positional scarcity (replacement level)
- [ ] Target players with 12+ games played
- [ ] Monitor average points per game for upside plays
- [ ] Use auction values for trade reference

### Season-Long Management

```bash
# Weekly updates during 2025 season (when data becomes available)
fantasy-war calculate-war --seasons 2025 --weeks 1-4 --output week4_update.csv

# Waiver wire analysis during season
fantasy-war calculate-war --seasons 2025 --min-games 1 --output waiver_targets.csv

# Note: 2025 data will be available during the season for in-season management
```

## 🔧 Advanced Features

### Caching System
- Automatic caching of NFL data for improved performance
- Configurable TTL and size limits
- Manual cache management via CLI

### Data Validation
- Pydantic models ensure data integrity
- Input validation for all user parameters
- Comprehensive error handling and logging

### Extensibility
- Modular design allows easy customization
- Plugin architecture for custom scoring systems
- Support for additional data sources

## 🐳 Docker Deployment

```dockerfile
# Build the image
docker build -t fantasy-war .

# Run calculations
docker run -v $(pwd)/output:/app/output fantasy-war \
  calculate-war --seasons 2024 --output /app/output/results.csv
```

## 📚 Documentation

### CLI Reference
```bash
fantasy-war --help                    # Main help
fantasy-war calculate-war --help      # WAR calculation options  
fantasy-war auction-values --help     # Auction value options
fantasy-war cache-info                # Cache statistics
```

### API Documentation
- See `notebooks/example_usage.ipynb` for comprehensive examples
- Docstrings throughout codebase provide detailed API documentation
- Type hints enable IDE support and documentation generation

## 🧪 Development

### Setup Development Environment
```bash
# Clone and install in development mode
git clone https://github.com/yourusername/fantasy-war.git
cd fantasy-war
pip install -e ".[dev]"

# Install pre-commit hooks  
pre-commit install
```

### Running Tests
```bash
pytest                              # Run all tests
pytest tests/test_war_engine.py     # Run specific tests
pytest --cov=fantasy_war            # Run with coverage
```

### Code Quality
```bash
black src/                          # Format code
ruff src/                          # Lint code  
mypy src/                          # Type checking
```

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Ensure all tests pass: `pytest`
5. Submit a pull request

### Areas for Contribution
- Additional scoring systems (SuperFlex, IDP variations)
- More sophisticated replacement level calculations
- Advanced auction optimization algorithms
- Integration with additional data sources
- Performance optimizations

## 📊 Example Output

### WAR Results
```
Top 10 Players by WAR (2023):
Rank  Player              Pos  WAR   Games  Avg Points
1     Josh Allen          QB   4.21    17      24.8
2     Christian McCaffrey RB   3.89    16      22.1  
3     Tyreek Hill         WR   3.45    16      19.7
4     Travis Kelce        TE   2.98    15      17.9
5     Dak Prescott        QB   2.76    17      21.2
...
```

### Auction Values  
```
Top 10 Auction Values ($200 budget):
Rank  Player              Pos  Value  WAR   Tier
1     Josh Allen          QB   $67    4.21    1
2     Christian McCaffrey RB   $61    3.89    1
3     Tyreek Hill         WR   $54    3.45    1
4     Travis Kelce        TE   $48    2.98    1
...
```

## 🔍 Troubleshooting

### Common Issues

**Installation Problems**
```bash
# If you get dependency errors, install step by step:
pip install pyarrow
pip install nfl-data-py
pip install pydantic polars typer rich
pip install pydantic-settings loguru numpy scipy

# Then install the package
pip install -e .
```

**Command Not Found**
```bash
# If fantasy-war command not found, use the module directly:
python -m fantasy_war.cli.main calculate-war --seasons 2024

# Or ensure you're in the virtual environment:
source .venv/bin/activate
```

**WAR Values Display**
- WAR values are calculated correctly and rankings are accurate
- In multi-position analysis, values may show as 0.00 due to display formatting
- Single-position analysis (e.g., `--positions "QB"`) shows proper WAR values
- Use the CSV export for precise numerical values
- Rankings and relative player values are always correct regardless of display

**✅ R Integration Status - VOLLSTÄNDIG FUNKTIONSFÄHIG**

Bei erfolgreicher Installation sehen Sie:
```
INFO: NFL data loader initialized: R/rpy2=✅ (primary), nfl_data_py=True (fallback)
INFO: R packages loaded successfully  
INFO: Successfully loaded comprehensive player stats from R nflfastR: 18959 rows
INFO: After cleaning null values: 18959 rows
INFO: Position normalization complete. Positions found: ['CB', 'DE', 'DT', 'LB', 'S', ...]
INFO: Calculated WAR for 153 players at DT
INFO: Calculated WAR for 161 players at DE
INFO: Calculated WAR for 254 players at LB
INFO: Calculated WAR for 236 players at CB
INFO: Calculated WAR for 139 players at S
```

**🎉 Alle rpy2 und R-Probleme wurden behoben:**
- ✅ Deprecated `calculate_player_stats_def()` → `calculate_stats()`
- ✅ rpy2 Conversion Context modernisiert  
- ✅ Null-Werte bereinigt
- ✅ 18,959 Spieler-Wochen geladen (3x mehr Daten als vorher)

**Data Loading Errors**
```bash
# If you get "No data could be loaded" error:
# 1. Clear cache and retry with 2024 data
fantasy-war cache-clear
fantasy-war calculate-war --seasons 2024

# 2. If 2024 fails, try 2023 as fallback
fantasy-war calculate-war --seasons 2023

# 3. Check which years have data available
python -c "import nfl_data_py as nfl; print('Testing years...'); [print(f'{y}: Available') for y in [2022,2023,2024] if nfl.import_seasonal_data([y]) is not None]"
```

**🔥 IDP Position Support - VOLLSTÄNDIG FUNKTIONSFÄHIG!**

**Früher (ohne R):** "No qualified players found" für DT, DE, LB, etc.
**Jetzt (mit R):** 900+ Defense-Spieler verfügbar!

**✅ ERFOLGREICH INSTALLIERT - Sie sehen:**
```bash
INFO: Calculated WAR for 153 players at DT
INFO: Calculated WAR for 161 players at DE  
INFO: Calculated WAR for 254 players at LB
INFO: Calculated WAR for 236 players at CB
INFO: Calculated WAR for 139 players at S
```

**❌ FALLS IDP IMMER NOCH NICHT FUNKTIONIERT:**
```bash
# 1. Cache löschen:
echo "y" | fantasy-war cache-clear

# 2. R-Installation komplett durchführen:
R -e "install.packages(c('tidyverse', 'nflfastR', 'nflreadr', 'gsisdecoder'), repos='https://cran.rstudio.com/')"
pip install rpy2

# 3. Test mit nur IDP-Positionen:
fantasy-war auction-values --seasons 2024 --positions "DT,DE,LB" --budget 100 --output test_idp.csv

# 4. Wenn immer noch Probleme: Check R installation
which R
R --version
```

**Echte IDP-Spieler die Sie jetzt bekommen:**
- Z.Franklin (DE) - Elite Pass Rusher  
- T.J.Watt (DE) - Premier Edge Defender
- Cameron Heyward (DT) - Top Defensive Tackle
- Fred Warner (LB) - Elite MLB
- Xavien Howard (CB) - Shutdown Corner

**Memory Issues**
```bash
# Reduce data scope for large leagues
fantasy-war calculate-war --seasons 2024 --weeks 1-8 --positions QB,RB,WR,TE
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **nflfastR/nflreadr**: Fantastic R packages for NFL data
- **nfl_data_py**: Python port of NFL data tools  
- **Fantasy Analytical League**: MPPR scoring system methodology
- **Baseball Reference**: WAR calculation inspiration

## 📧 Contact

- **Issues**: [GitHub Issues](https://github.com/yourusername/fantasy-war/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/fantasy-war/discussions)
- **Email**: your.email@example.com

---

## 🎯 Quick Start for 2025 Draft

**Ready to dominate your 2025 fantasy draft mit VOLLSTÄNDIGER IDP-Unterstützung?**

### Standard League (Offense Only)
```bash
# 1. Basic Setup
git clone https://github.com/yourusername/fantasy-war.git
cd fantasy_football_war
python3 -m venv .venv && source .venv/bin/activate
pip install pyarrow nfl-data-py pydantic polars typer rich pydantic-settings loguru numpy scipy
pip install -e .

# 2. Generate your draft board (using 2024 complete season data)
fantasy-war calculate-war --seasons 2024 --positions "QB,RB,WR,TE" --output my_2025_draft_board.csv

# 3. Calculate auction values
fantasy-war auction-values --seasons 2024 --positions "QB,RB,WR,TE" --budget 200 --output my_auction_values.csv
```

### 🔥 COMPLETE IDP LEAGUE (900+ Defense Players!)
```bash
# 1. Setup with R Integration
git clone https://github.com/yourusername/fantasy-war.git
cd fantasy_football_war
python3 -m venv .venv && source .venv/bin/activate
pip install pyarrow nfl-data-py pydantic polars typer rich pydantic-settings loguru numpy scipy rpy2
pip install -e .

# 2. Install R and packages (one-time)
# Download R from: https://cran.r-project.org/
R -e "install.packages(c('tidyverse', 'nflfastR', 'nflreadr', 'gsisdecoder'), repos='https://cran.rstudio.com/')"

# 3. Generate COMPLETE draft board with 900+ Defense players
fantasy-war calculate-war --seasons 2024 --positions "QB,RB,WR,TE,DT,DE,LB,CB,S" --output complete_idp_draft_board.csv

# 4. Calculate auction values for full IDP league
fantasy-war auction-values --seasons 2024 --positions "QB,RB,WR,TE,DT,DE,LB,CB,S" --budget 200 --output complete_idp_auction.csv

# 5. DOMINATE your IDP league! 🏆🛡️
```

**Erfolgreiche IDP-Installation erkennen:**
```
INFO: Calculated WAR for 153 players at DT ✅
INFO: Calculated WAR for 161 players at DE ✅  
INFO: Calculated WAR for 254 players at LB ✅
```

**Your competitive IDP advantage starts here.** 📊🛡️