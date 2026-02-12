"""Main scraping logic for FOIA documents."""

import requests
import sys
from bs4 import BeautifulSoup
import time
import pandas as pd
from pathlib import Path
from urllib.parse import urljoin
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

        rows = tbody.find_all('tr')

        metadata_csv_dict_list = []

        for row in rows:
            cells = row.find_all('td')
            foi_number = cells[0].text.strip()
            foi_date_machine = cells[1].find('time')['datetime']
            foi_date_human_readable = cells[1].text.strip()
            foi_title = cells[2].text.strip()
            foi_href = cells[2].find('a').get('href')
            foi_link = urljoin(self.base_url, foi_href)
            
            metadata_csv_dict = {
                "FOI Number": foi_number,
                "FOI Date (Machine)": foi_date_machine,
                "FOI Date (Human)": foi_date_human_readable,
                "FOI Title": foi_title,
                "FOI URL": foi_link 
            }

            metadata_csv_dict_list.append(metadata_csv_dict)
        
        return metadata_csv_dict_list

    def save_metadata_to_csv(self, metadata_list, csv_name):
        df = pd.DataFrame(metadata_list)
        df.to_csv(f"./data/metadata/{csv_name}.csv", index=False)
    
    def find_pdf_url(self, csv_filepath):
        df = pd.read_csv(csv_filepath)
        link_list = df['FOI URL'].tolist()
        error_list = []
        for link in link_list:
            try:   
                response = requests.get(link)
                soup = BeautifulSoup(response.content, 'html.parser')
                pdf_href = soup.find('a', 'health-file__link').get('href')
                pdf_url = urljoin(self.base_url, pdf_href)
                self.download_pdf(pdf_url, "./data/raw/")
            except:
                error_list.append({
                    "Link": link,
                    "Error Type": sys.exc_info()[0]
                })
        df = pd.DataFrame(error_list)
        df.to_csv(f"./data/errors.csv", index=False)


    def download_pdf(self, pdf_url, filepath):
        response = requests.get(pdf_url)
        pdf_name = pdf_url.split('/')[-1]
        with open(f"{filepath}{pdf_name}", 'wb') as f:
            f.write(response.content)
