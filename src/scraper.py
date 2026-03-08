"""Main scraping logic for FOIA documents."""

import requests
import sys
from bs4 import BeautifulSoup
import time
import pandas as pd
from pathlib import Path
from urllib.parse import urljoin
from src.config import SOURCES, HEADERS, DELAY_BETWEEN_REQUESTS, DOWNLOAD_DIR, MAX_DOCUMENTS, METADATA_FILE

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

        if Path(METADATA_FILE).exists():
            metadata_df = pd.read_csv(METADATA_FILE)
            processed_links = set(metadata_df['FOI URL'])
        else:
            metadata_df = pd.DataFrame(columns=["FOI Number"
                                               ,"FOI Date (Machine)"
                                               ,"FOI Date (Human)"
                                               ,"FOI Title"
                                               ,"FOI URL"
                                               ,"PDF INDEX"
                                               ,"PDF COUNT" 
                                               ,"PDF URL"
                                               ,"Processed"])
            processed_links = set()

        metadata_csv_dict_list = []

        for row in rows:
            cells = row.find_all('td')
            foi_number = cells[0].text.strip()
            foi_date_machine = cells[1].find('time')['datetime']
            foi_date_human_readable = cells[1].text.strip()
            foi_title = cells[2].text.strip()
            foi_href = cells[2].find('a').get('href')
            foi_link = urljoin(self.base_url, foi_href)
            
            if foi_link not in processed_links:
                processed_links.add(foi_link)
                metadata_csv_dict = {
                    "FOI Number": foi_number,
                    "FOI Date (Machine)": foi_date_machine,
                    "FOI Date (Human)": foi_date_human_readable,
                    "FOI Title": foi_title,
                    "FOI URL": foi_link,
                    "PDF INDEX": 0,
                    "PDF COUNT": 0, 
                    "PDF URL": "No URL",
                    "Processed": "Unprocessed"
                    }
                metadata_csv_dict_list.append(metadata_csv_dict)
            else:
                pass
        print(f"{len(metadata_csv_dict_list)} new rows found")
        return metadata_csv_dict_list

    def save_metadata_to_csv(self, metadata_list):
        if len(metadata_list) == 0:
            print("No new metadata")
            return
        else:
            df = pd.DataFrame(metadata_list)
            if Path(METADATA_FILE).exists():
                metadata_df = pd.read_csv(METADATA_FILE)
                metadata_df = pd.concat([metadata_df, df], ignore_index=True)
                metadata_df.to_csv(METADATA_FILE, index=False)
            else:
                df.to_csv(METADATA_FILE, index=False)
    
    def find_pdf_url(self):
        df = pd.read_csv(METADATA_FILE)
        processed_df = df.loc[df["Processed"].isin(["Downloaded", "No PDF"])]
        unprocessed_df = df.loc[~df["Processed"].isin(["Downloaded", "No PDF"])]
        unprocessed_rows = len(unprocessed_df)
        #unprocessed_rows = (df["Processed"]== "Unprocessed").sum()
        print(f"{unprocessed_rows} number of new links found")
        processed_rows = 0
        newly_processed_list = []
        for i, row in unprocessed_df.iterrows():
            (foi_number, foi_date_machine, foi_date_human, 
                foi_title, foi_url, pdf_index, pdf_count,
                pdf_url, processed) = row
            processed_rows += 1
            link = row["FOI URL"]
            try:
                response = self.session.get(link)
                soup = BeautifulSoup(response.content, 'html.parser')
                pdf_link_tags = soup.find_all('a', 'health-file__link')
                if not pdf_link_tags:
                    processed = "No PDF"
                    metadata_csv_dict = {
                            "FOI Number": foi_number,
                            "FOI Date (Machine)": foi_date_machine,
                            "FOI Date (Human)": foi_date_human,
                            "FOI Title": foi_title,
                            "FOI URL": foi_url,
                            "PDF INDEX": 0,
                            "PDF COUNT": 0,  
                            "PDF URL": pdf_url,
                            "Processed": processed,
                            }
                    newly_processed_list.append(metadata_csv_dict)
                else:
                    pdf_count = len(pdf_link_tags)
                    for n, pdf_tag in enumerate(pdf_link_tags):
                        pdf_href = pdf_tag.get('href')
                        pdf_url = urljoin(self.base_url, pdf_href)
                        self.download_pdf(pdf_url)
                        pdf_index = n+1
                        processed = "Downloaded"
                        metadata_csv_dict = {
                            "FOI Number": foi_number,
                            "FOI Date (Machine)": foi_date_machine,
                            "FOI Date (Human)": foi_date_human,
                            "FOI Title": foi_title,
                            "FOI URL": foi_url,
                            "PDF INDEX": pdf_index,
                            "PDF COUNT": pdf_count,  
                            "PDF URL": pdf_url,
                            "Processed": processed,
                            }
                        newly_processed_list.append(metadata_csv_dict)
            except requests.exceptions.RequestException as e:
                processed = f"Network Error {e}"
                pdf_url = ""
                metadata_csv_dict = {
                            "FOI Number": foi_number,
                            "FOI Date (Machine)": foi_date_machine,
                            "FOI Date (Human)": foi_date_human,
                            "FOI Title": foi_title,
                            "FOI URL": foi_url,
                            "PDF INDEX": 0,
                            "PDF COUNT": 0,  
                            "PDF URL": pdf_url,
                            "Processed": processed,
                }
                newly_processed_list.append(metadata_csv_dict)
            except Exception as e:
                processed = f"Exception {e}"
                pdf_url = ""
                metadata_csv_dict = {
                            "FOI Number": foi_number,
                            "FOI Date (Machine)": foi_date_machine,
                            "FOI Date (Human)": foi_date_human,
                            "FOI Title": foi_title,
                            "FOI URL": foi_url,
                            "PDF INDEX": 0,
                            "PDF COUNT": 0,  
                            "PDF URL": pdf_url,
                            "Processed": processed,
                }
                newly_processed_list.append(metadata_csv_dict)
            print(f"{processed_rows} out of {unprocessed_rows} processed")
            time.sleep(DELAY_BETWEEN_REQUESTS)   
        newly_processed_df = pd.DataFrame(newly_processed_list)
        df = pd.concat([processed_df, newly_processed_df], ignore_index=True)
        df.to_csv(METADATA_FILE, index=False)

    def download_pdf(self, pdf_url):
        pdf_name = pdf_url.split('/')[-1]
        path = Path(DOWNLOAD_DIR, pdf_name)
        if path.exists():
            print(f"PDF already exists. Skipping {pdf_name}")
            return
        response = self.session.get(pdf_url)
        with open(f"{DOWNLOAD_DIR}/{pdf_name}", 'wb') as f:
            f.write(response.content)
    
    def get_all_pages(self, soup, base_url):
        last_li = soup.find('li', 'pager__item pager__item--last')
        last_link = last_li.find('a')
        href = last_link.get('href')
        max_page_number = int(href.split('=')[1])
        #print(max_page_number)
        for i in range(0, max_page_number+1):
            url = urljoin(base_url, f'?page={i}')
            response = self.session.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            metadata = self.parse_table(soup)
            self.save_metadata_to_csv(metadata)
            if i < max_page_number:
                time.sleep(DELAY_BETWEEN_REQUESTS)