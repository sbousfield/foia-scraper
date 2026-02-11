"""Main scraping logic for FOIA documents."""

import requests
from bs4 import BeautifulSoup
import time
import pandas as pd
from pathlib import Path
from src.config import SOURCES, HEADERS, DELAY_BETWEEN_REQUESTS, DOWNLOAD_DIR, MAX_DOCUMENTS

class FOIScraper:
    """Scraper for Australian FOIA documents."""
    
    def __init__(self, source_name='Dept Health'):
        """Initialize the scraper.
        
        Args:
            source_name: Which source to scrape (key from SOURCES dict)
        """
        self.source_name = source_name
        self.base_url = SOURCES[source_name]
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.documents = []  # Will store metadata about downloaded docs
        
    def test_connection(self):
        """Test if we can connect to the website."""
        try:
            response = self.session.get(self.base_url, timeout=10)
            response.raise_for_status()
            print(f"✓ Successfully connected to {self.base_url}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect: {e}")
            return False
    
    def parse_table(self, soup):
        """Extract metadata from the disclosure log table."""
        table = soup.find('table')
        thead = soup.find('thead')
        tbody = soup.find('tbody')
        
        if not table:
            print("Table not found")
            return []
        
        print("Found table")

        rows = tbody.find_all('tr')
        print(f"found {len(rows)} rows")

        """for row in rows:
            cells = row.find_all('td')
            foi_number = cells[0].text.strip()
            foi_date_machine = cells[1].find('time')['datetime']
            foi_date_human_readable = cells[1].text.strip
            foi_title = cells[2].text.strip()
            foi_link = cells[2].find('a').get('href')
            """

        if len(rows) > 1:
            test_row = rows[1]
            cells = test_row.find_all('td')
            #for i, cell in enumerate(cells):
            #    print(f"Column {i}: {cell.text.strip()[:50]}")
            foi_number = cells[1].find('time')['datetime']
            print(foi_number)
        return []