import os
import pymupdf
import easyocr
from pdf2image import convert_from_path
import time
import json
import numpy as np
import re
import sqlite3
import pandas as pd
from pathlib import Path
from src.config import PROCESSED_DIR, DOWNLOAD_DIR

class PDFExtractor:

    def sqlite_database_connect(self, db):
        db = str(Path(PROCESSED_DIR/db))
        if not os.path.exists(db):
            conn = sqlite3.connect(db)
            curs = conn.cursor()
            curs.execute('DROP TABLE IF EXISTS DOCUMENTS')
            curs.execute('DROP TABLE IF EXISTS PAGES')
            create_table_documents = """
                            CREATE TABLE DOCUMENTS (
                                FILENAME PRIMARY KEY,
                                FOI_REFERENCE_NUMBER,
                                PAGE_COUNT,
                                DOCUMENT_WORD_COUNT
                            );
                            """
            create_table_pages = """
                            CREATE TABLE PAGES (
                                FILENAME,
                                FOI_REFERENCE_NUMBER,
                                PYTHON_PAGE_NUMBER,
                                HUMAN_PAGE_NUMBER,
                                RAW_TEXT,
                                WORD_COUNT,
                                DATE_PROCESSED,
                                WATERMARK_REMOVED,
                                EXTRACTION_METHOD,
                                PRIMARY KEY(FILENAME, PYTHON_PAGE_NUMBER)
                            );
                            """
            # create_document_index_filename = """CREATE UNIQUE INDEX document_filename
            #                                 ON DOCUMENTS (FILENAME)"""
            # create_document_index_foi_ref = """CREATE UNIQUE INDEX document_foi_reference
            #                                 ON DOCUMENTS (FOI_REFERENCE_NUMBER)"""


            # create_pages_index_file_page = """CREATE UNIQUE INDEX pages_file_page
            #                                 ON PAGES (FILENAME, PYTHON_PAGE_NUMBER)"""
            # create_pages_index_foi_page = """CREATE UNIQUE INDEX pages_foi_page
            #                                 ON PAGES (FOI_REFERENCE_NUMBER, PYTHON_PAGE_NUMBER)"""
            #Create Tables
            curs.execute(create_table_documents)
            curs.execute(create_table_pages)
            #Create Indexes
            # PK's already provide indexes
            # curs.execute(create_document_index_filename)
            # curs.execute(create_document_index_foi_ref)
            # curs.execute(create_pages_index_foi_page)
            # curs.execute(create_pages_index_file_page)
            #Commit
            conn.commit()
        else:
            conn = sqlite3.connect(db)
            curs = conn.cursor()
        return conn, curs

    def remove_watermarks(self, s) :
        foi_watermark_pattern = r"FOI\d+-\d+(?:\w+)?(?:-)?(?:DOCUMENT\d*)?"
        pagenumber_watermark_pattern = r"PAGE\d+OF\d+"
        #remove whitespace
        s = re.sub(r"\s+", "", s, flags=re.IGNORECASE)
        #remove known watermark patters
        s = re.sub(foi_watermark_pattern, "", s, flags=re.IGNORECASE)
        s = re.sub(pagenumber_watermark_pattern, "", s, flags=re.IGNORECASE)
        return s

    def pdf_processing(self, curs):
        curs.execute("SELECT FILENAME FROM DOCUMENTS")
        processed_documents = {row[0] for row in curs.fetchall()}
        for pdf in os.listdir(DOWNLOAD_DIR):
            if not pdf.lower().endswith(".pdf"):
                continue
            elif pdf in processed_documents:
                continue
            try:
                processing_time_start = time.time()
                date_processed = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(processing_time_start))
                filename = pdf
                foi_reference_number = filename[:-4]
                document = pymupdf.open(DOWNLOAD_DIR/pdf)
                total_pages = len(document)
                document_word_count = 0
                curs.execute("""INSERT INTO DOCUMENTS (FILENAME, FOI_REFERENCE_NUMBER, PAGE_COUNT, DOCUMENT_WORD_COUNT) 
                            VALUES (?, ?, ?, ?)""", (filename, foi_reference_number, total_pages, document_word_count)
                            )
            except Exception as e:
                print(f"Error processing {pdf}: {e}")
                with open(Path(PROCESSED_DIR/'errors.txt'), 'a') as f:
                    print(f"{date_processed} - Error Processing ({pdf}): {e}", file=f) 
                continue
            document.close()
    
    def processed_already(self, pdf, curs):
        documents_row = curs.execute("SELECT FILENAME, FOI_REFERENCE_NUMBER, PAGE_COUNT, DOCUMENT_WORD_COUNT FROM DOCUMENTS WHERE FILENAME = ?", (pdf,)).fetchone()
        if documents_row is None:
            return None
        filename, foi_reference_number, page_count, document_word_count = documents_row
        curs.execute("SELECT PYTHON_PAGE_NUMBER FROM PAGES WHERE FILENAME = ?", (filename,))
        processed_pages = {row[0] for row in curs.fetchall()}
        return processed_pages, filename, foi_reference_number, page_count, document_word_count

    def pdf_native_text_extraction(self, curs, conn):
        for pdf in os.listdir(DOWNLOAD_DIR):
            if not pdf.lower().endswith(".pdf"):
                continue
            document = pymupdf.open(DOWNLOAD_DIR/pdf)
            processing_time_start = time.time()
            date_processed = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(processing_time_start))
            newly_processed_pages = 0
            try:
                results = self.processed_already(pdf, curs)
                if results is None:
                    continue
                processed_pages, filename, foi_reference_number, page_count, document_word_count = results         
                extraction_method = 'NATIVE'
                watermark = 'N/A'
                # MOVED TO ITS OWN FUNCTION
                # documents_row = curs.execute("SELECT FILENAME, FOI_REFERENCE_NUMBER, PAGE_COUNT, DOCUMENT_WORD_COUNT FROM DOCUMENTS WHERE FILENAME = ?", (pdf,)).fetchone()
                # if documents_row is None:
                #     continue
                # filename, foi_reference_number, page_count, document_word_count = documents_row
                # # filename = documents_row[0]
                # # foi_reference_number = documents_row[1]
                # # page_count = documents_row[2]
                # # document_word_count = documents_row[3]
                # curs.execute("SELECT PYTHON_PAGE_NUMBER FROM PAGES WHERE FILENAME = ?", (filename,))
                # processed_pages = {row[0] for row in curs.fetchall()}
                for i, page in enumerate(document):
                    if i in processed_pages:
                        continue
                    python_page_number = i
                    human_page_number = i+1
                    contents = ''
                    blocks = page.get_text("dict")["blocks"]
                    for block in blocks:
                        if block['type'] == 0:
                            for line in block['lines']:
                                if int(abs(line['dir'][0]) * 10_000) != 7071:  # skip watermark
                                    for span in line['spans']:
                                        contents += span['text']
                                    contents += '\n'
                            contents += '\n'

                    if len(self.remove_watermarks(contents)) == 0:
                        contents = None
                        word_count = 0
                    else:
                        word_count = len(contents.split())
                        document_word_count += word_count
                    ###TODO: COMMENT HERE
                    if contents is None:
                        continue
                    else:
                        curs.execute("""INSERT INTO PAGES (FILENAME, FOI_REFERENCE_NUMBER, PYTHON_PAGE_NUMBER, HUMAN_PAGE_NUMBER, RAW_TEXT, WORD_COUNT, DATE_PROCESSED, WATERMARK_REMOVED, EXTRACTION_METHOD) 
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", (filename, foi_reference_number, python_page_number, human_page_number, contents, word_count, date_processed, watermark, extraction_method)
                                    )
                        newly_processed_pages += 1
                curs.execute("""UPDATE DOCUMENTS
                                SET DOCUMENT_WORD_COUNT = ?
                                WHERE 1=1
                                AND FILENAME = ?
                                AND FOI_REFERENCE_NUMBER = ?
                                AND PAGE_COUNT = ?""", (document_word_count, filename, foi_reference_number, page_count))
                conn.commit()
            except Exception as e:
                print(f"Error processing {pdf}: {e}")
                with open(Path(PROCESSED_DIR/'errors.txt'), 'a') as f:
                    print(f"{date_processed} - Error Processing ({pdf}): {e}", file=f) 
                continue
            document.close()



    def pdf_ocr_text_extraction(self, curs, conn):
        reader = easyocr.Reader(['en'], gpu=True)
        # DPI chosen from analysis of a small corpus of documents in my test file/notebook
        # This is an obvious and easy change to make to see if other values return a better
        # file across multiple documents 
        DPI = 400
        for pdf in os.listdir(DOWNLOAD_DIR):
            if not pdf.lower().endswith(".pdf"):
                continue
            document = pymupdf.open(DOWNLOAD_DIR/pdf)
            cat = document.pdf_catalog()
            processing_time_start = time.time()
            date_processed = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(processing_time_start))
            newly_processed_pages = 0
            try:
                results = self.processed_already(pdf, curs)
                if results is None:
                    continue
                processed_pages, filename, foi_reference_number, page_count, document_word_count = results
                extraction_method = 'OCR'
                watermark_xrefs = [xref for xref, props in document.get_ocgs().items() if props['name'] == 'Watermark']
                if watermark_xrefs:
                    off_array = ' '.join(f"{xref} 0 R" for xref in watermark_xrefs)
                    document.xref_set_key(cat, "OCProperties/D/ON", "[]")
                    document.xref_set_key(cat, "OCProperties/D/OFF", f"[{off_array}]")
                watermark = json.dumps({'xrefs': watermark_xrefs, 'contents': {str(k): v for k, v in document.get_ocgs().items()}})
                tmp_path = '/tmp/tmp'+pdf
                document.save(tmp_path)
                document.close()
                #tmp_pdf = pdf with watermarks removed
                tmp_pdf = pymupdf.open(tmp_path)
                for i, page in enumerate(tmp_pdf):
                    if i in processed_pages:
                        continue
                    python_page_number = i
                    human_page_number = i+1
                    contents = ''
                    pix = page.get_pixmap(matrix=pymupdf.Matrix(DPI/72, DPI/72))
                    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                    # print(f"width={pix.width} height={pix.height} n={pix.n} samples_len={len(pix.samples)}")
                    reader_text = reader.readtext(img[:,:,:3], detail=0)
                    contents = ' '.join(reader_text)
                    word_count = len(contents.split())
                    document_word_count += word_count
                    curs.execute("""INSERT INTO PAGES (FILENAME, FOI_REFERENCE_NUMBER, PYTHON_PAGE_NUMBER, HUMAN_PAGE_NUMBER, RAW_TEXT, WORD_COUNT, DATE_PROCESSED, WATERMARK_REMOVED, EXTRACTION_METHOD) 
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", (filename, foi_reference_number, python_page_number, human_page_number, contents, word_count, date_processed, watermark, extraction_method)
                                    )
                    newly_processed_pages += 1       
                curs.execute("""UPDATE DOCUMENTS
                                SET DOCUMENT_WORD_COUNT = ?
                                WHERE 1=1
                                AND FILENAME = ?
                                AND FOI_REFERENCE_NUMBER = ?
                                AND PAGE_COUNT = ?""", (document_word_count, filename, foi_reference_number, page_count))
                conn.commit()
            except Exception as e:
                print(f"Error processing {pdf}: {e}")
                with open(Path(PROCESSED_DIR/'errors.txt'), 'a') as f:
                    print(f"{date_processed} - Error Processing ({pdf}): {e}", file=f) 
                continue
            tmp_pdf.close()
            os.remove(tmp_path)