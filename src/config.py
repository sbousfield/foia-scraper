"""Configuration for FOIA scraper."""

from pathlib import Path
# Target websites
SOURCES = {
    'Dept Health': 'https://www.health.gov.au/resources/foi-disclosure-log',
    # We'll add more sources later if needed
}

# Scraping settings
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DOWNLOAD_DIR = PROJECT_ROOT/'data/raw'
METADATA_FILE = PROJECT_ROOT/'data/metadata/scraped_docs.csv'
DELAY_BETWEEN_REQUESTS = 2  # seconds - be polite to servers
MAX_RETRIES = 3
MAX_DOCUMENTS = 50  # Limit for initial scraping

# Headers to avoid being blocked
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}