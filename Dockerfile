# Fantasy Football WAR Calculator - Docker Image
FROM python:3.11-slim

LABEL maintainer="Christian Lohr <your.email@example.com>"
LABEL description="Fantasy Football WAR Calculator with MPPR scoring"
LABEL version="0.1.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VENV_IN_PROJECT=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # R and R packages dependencies
    r-base \
    r-base-dev \
    # Build dependencies
    gcc \
    g++ \
    make \
    # Git for any git-based pip installs
    git \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install R packages needed for nflfastR integration (including gsisdecoder for complete IDP support)
RUN R -e "install.packages(c('tidyverse', 'nflfastR', 'nflreadr', 'gsisdecoder'), repos='https://cran.rstudio.com/', lib='/usr/lib/R/site-library')"

# Create app user (security best practice)
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy requirements first
COPY pyproject.toml ./
COPY README.md ./

# Copy application code (needed for version detection)
COPY src/ ./src/
COPY notebooks/ ./notebooks/

# Install Python dependencies
RUN pip install --upgrade pip \
    && pip install .

# Create data and cache directories
RUN mkdir -p /app/data/cache /app/output \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set default environment variables for container
ENV FANTASY_WAR_CACHE_ENABLED=true \
    FANTASY_WAR_DATA_START_YEAR=2014 \
    FANTASY_WAR_LOGGING_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD fantasy-war --help || exit 1

# Default command
ENTRYPOINT ["fantasy-war"]
CMD ["--help"]

# Usage examples:
# Build: docker build -t fantasy-war .
# 
# 🔥 COMPLETE IDP AUCTION with 900+ Defense Players:
# docker run -v $(pwd)/output:/app/output fantasy-war \
#   auction-values --seasons 2024 --positions "QB,RB,WR,TE,DT,DE,LB,CB,S" --budget 200 --output /app/output/complete_idp_auction.csv
#
# Standard Auction (Offense only):
# docker run -v $(pwd)/output:/app/output fantasy-war \
#   auction-values --seasons 2024 --positions "QB,RB,WR,TE" --budget 200 --output /app/output/auction_values.csv
#
# Calculate WAR:
# docker run -v $(pwd)/output:/app/output fantasy-war \
#   calculate-war --seasons 2024 --output /app/output/war_results.csv
#
# Interactive shell:
# docker run -it --rm fantasy-war bash