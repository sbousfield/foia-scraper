"""Entry point for FOIA scraper."""

from bs4 import BeautifulSoup
from src.scraper import FOIScraper
from pathlib import Path

def main():
    """Main function to run the scraper."""
    # Ensure directories exist
    Path('data/raw').mkdir(parents=True, exist_ok=True)
    Path('data/metadata').mkdir(parents=True, exist_ok=True)
    
    print("=== FOIA Document Scraper ===\n")
    
    # Initialize scraper
    scraper = FOIScraper('Dept Health')
    
    # Test connection
    if scraper.test_connection():
        #print("\nReady to start scraping!")
        response = scraper.session.get(scraper.base_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        metadata = scraper.parse_table(soup)
        scraper.save_metadata_to_csv(metadata, "dept_health_metadata")
        scraper.find_pdf_url("./data/metadata/dept_health_metadata.csv")
    else:
        print("\nCannot proceed - connection failed.")
        return

if __name__ == '__main__':
    main()