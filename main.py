"""Entry point for FOIA scraper."""

from src.config import DOWNLOAD_DIR, TEST_PDF_DIR
from bs4 import BeautifulSoup
from src.scraper import FOIScraper
from pathlib import Path
from src.config import PROJECT_ROOT
from src.pdf_processing import PDFExtractor

def main():
    """Main function to run the scraper."""
    # Ensure directories exist
    Path(PROJECT_ROOT, 'data/raw').mkdir(parents=True, exist_ok=True)
    Path(PROJECT_ROOT, 'data/metadata').mkdir(parents=True, exist_ok=True)
    
    """print("=== FOIA Document Scraper ===\n")
    # Initialize scraper
    scraper = FOIScraper('Dept Health')
    
    # Test connection
    if scraper.test_connection():
        #print("\nReady to start scraping!")
        response = scraper.session.get(scraper.base_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        scraper.get_all_pages(soup, scraper.base_url)
        scraper.find_pdf_url()
        
    else:
        print("\nCannot proceed - connection failed.")"""
    extractor = PDFExtractor()
    conn, curs = extractor.sqlite_database_connect('processed_documents.db') 
    extractor.pdf_processing(conn, curs, TEST_PDF_DIR)
    extractor.pdf_native_text_extraction(conn, curs, TEST_PDF_DIR)
    extractor.pdf_ocr_text_extraction(conn, curs, TEST_PDF_DIR)
    conn.close()

if __name__ == '__main__':
    main()