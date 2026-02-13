"""Entry point for FOIA scraper."""

from bs4 import BeautifulSoup
from src.scraper import FOIScraper
from pathlib import Path
from src.config import PROJECT_ROOT

def main():
    """Main function to run the scraper."""
    # Ensure directories exist
    Path(PROJECT_ROOT, 'data/raw').mkdir(parents=True, exist_ok=True)
    Path(PROJECT_ROOT, 'data/metadata').mkdir(parents=True, exist_ok=True)
    
    print("=== FOIA Document Scraper ===\n")
    # Initialize scraper
    scraper = FOIScraper('Dept Health')
    
    # Test connection
    if scraper.test_connection():
        #print("\nReady to start scraping!")
        response = scraper.session.get(scraper.base_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        scraper.get_all_pages(soup, scraper.base_url)
        exit()
        scraper.find_pdf_url()
        
    else:
        print("\nCannot proceed - connection failed.")
        return

if __name__ == '__main__':
    main()