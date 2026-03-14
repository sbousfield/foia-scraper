# FOIA Redaction Auditor

An end-to-end data science pipeline to scrape, extract, and analyse Australian government Freedom of Information documents — auditing redaction quality using NLP and PII detection.

---

## Overview

Australian government agencies are required by law to publish FOI disclosure logs containing released documents. This project builds a complete pipeline to collect those documents and programmatically audit whether PII has been properly redacted before release.

**The pipeline:**
1. Scrapes the Department of Health FOI disclosure log and downloads PDFs
2. Extracts text using a two-path approach: native text extraction for digital PDFs, GPU-accelerated OCR for scanned pages
3. Detects PII using regex patterns and Named Entity Recognition
4. Analyses redaction quality and patterns across the corpus

**Key finding:** Redaction at the Department of Health appears effective. This is itself a meaningful result — it validates the department's manual redaction process and demonstrates a methodology that could be applied to audit other agencies or catch failures at higher document volumes.

---

## Project Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Web scraper | ✅ Complete |
| 2 | Extraction method comparison (notebook) | ✅ Complete |
| 3 | Production extraction pipeline | ✅ Complete |
| 4 | PII detection & analysis | 🔄 In Progress |

---

## Technical Highlights

- **1,264 PDFs** scraped (~5.4 GB), across two scrape runs with resume capability
- **Two-path extraction:** pymupdf span-level extraction for native text; EasyOCR at 400 DPI for scanned pages
- **Watermark removal:** Every page carries a diagonal FOI watermark on a separate PDF Optional Content Group (OCG) layer — toggled off programmatically before OCR rendering
- **1,173 documents** extracted natively; **464 documents** required OCR (partial or full)
- **~8 hours** total pipeline runtime on RTX 2060 Super (6GB VRAM)
- Results stored in **SQLite** (~160MB) with page-level checkpointing for crash-safe overnight runs

---

## Pipeline Architecture

### Phase 1: Scraper

Targets the [Department of Health FOI disclosure log](https://www.health.gov.au/resources/foi-disclosure-log), handling 16 pages of pagination (~50 documents per page).

Ethical scraping practices:
- Checked `robots.txt` before scraping (disclosure log not disallowed, no crawl-delay specified)
- 2-second delays between all requests
- Proper User-Agent headers
- Incremental saving — crash-safe, restartable

Metadata tracked per PDF:
```
FOI Number | Date | Title | FOI URL | PDF Index | PDF Count | PDF URL | Status
```

---

### Phase 2: Extraction Method Comparison

11 documents were purposively sampled to cover key document types and edge cases:
- Native text (clean, minimal redactions)
- Scanned images (no text layer)
- Mixed pages
- Heavily redacted documents
- Diary layouts, email trails, calendar screenshots

Four extraction methods were tested:

| Method | Watermark Handling | Scanned Docs | Selected |
|--------|-------------------|--------------|----------|
| pdfplumber | ❌ Garbled diagonal text | ❌ | No |
| pymupdf native | ✅ Filtered via span direction | ❌ | ✅ Native pages |
| pytesseract | ✅ | ✅ | No — CPU-bound, linear scaling |
| EasyOCR (GPU) | ✅ After OCG removal | ✅ | ✅ Scanned pages |

---

### Phase 3: Production Extraction Pipeline

```
PDF
├── pymupdf native extraction
│   ├── Filter diagonal spans (watermark, detected via line['dir'])
│   ├── Filter boilerplate (FOI reference headers, page numbers)
│   └── If empty after filtering → not inserted → flagged for OCR path
└── EasyOCR path (pages absent from PAGES table)
    ├── Disable OCG watermark layer via PDF catalog manipulation
    ├── Save to temp file, reload
    ├── Render at 400 DPI via get_pixmap()
    └── Run EasyOCR with GPU acceleration
```

#### Watermark handling (native)
The diagonal watermark is filtered by detecting non-horizontal text spans:
```python
if int(abs(line['dir'][0]) * 10_000) != 7071:  # skip diagonal spans
```

#### Watermark handling (OCR)
The watermark OCG layer is disabled before rendering, removing it cleanly from the rasterised image:
```python
watermark_xrefs = [xref for xref, props in document.get_ocgs().items() if props['name'] == 'Watermark']
if watermark_xrefs:
    off_array = ' '.join(f"{xref} 0 R" for xref in watermark_xrefs)
    document.xref_set_key(cat, "OCProperties/D/ON", "[]")
    document.xref_set_key(cat, "OCProperties/D/OFF", f"[{off_array}]")
```

#### SQLite schema
```sql
CREATE TABLE DOCUMENTS (
    FILENAME TEXT PRIMARY KEY,
    FOI_REFERENCE_NUMBER TEXT,
    PAGE_COUNT INTEGER,
    DOCUMENT_WORD_COUNT INTEGER
);

CREATE TABLE PAGES (
    FILENAME TEXT,
    FOI_REFERENCE_NUMBER TEXT,
    PYTHON_PAGE_NUMBER INTEGER,
    HUMAN_PAGE_NUMBER INTEGER,
    RAW_TEXT TEXT,
    CLEANED_TEXT TEXT,
    WORD_COUNT INTEGER,
    DATE_PROCESSED TEXT,
    WATERMARK_REMOVED TEXT,
    EXTRACTION_METHOD TEXT,      -- 'NATIVE' or 'OCR'
    PRIMARY KEY(FILENAME, PYTHON_PAGE_NUMBER)
);
```

---

### Phase 4: PII Detection & Analysis (In Progress)

#### Text cleaning
A corpus-wide character audit identified non-standard characters requiring normalisation before NLP:
- Ligatures (`ﬁ`, `ﬂ`, `ﬀ`, `ﬃ`, `Ɵ`, `Ō`, `ƫ`) → will be expanded to standard ASCII
- Whitespace variants (`\xa0`, `\u202f`, `\u2009`) → will be normalised to space
- Zero-width characters (`\u200b`, `\u200c`, `\u200d`) → will be stripped
- Control characters → will be stripped
- Unmapped font characters (`\uf0XX` Wingdings range) → will be stripped

Cleaned text will be stored in a `CLEANED_TEXT` column, preserving `RAW_TEXT` as a faithful extraction record.

#### PII detection (planned, two-track)

**Regex-based** (high precision, structured PII):
- Email addresses
- Australian phone numbers (mobile, landline, international format)
- Medicare numbers
- Tax File Numbers (TFN)

**Named Entity Recognition** (spaCy):
- Person names (`PERSON`)
- Organisations (`ORG`)
- Locations (`GPE`, `LOC`)

#### Analysis (planned)
- Frequency and distribution of FOI exemption codes (`s47F`, `s47C`, `s22`, `s47E(d)`, `s47G`)
- PII detection rates across document types and extraction methods
- Assessment of redaction consistency

#### Ethical considerations
- No specific PII discovered will be published
- Only aggregate statistics will be reported
- Findings may be reported to the Office of the Australian Information Commissioner (OAIC)

---

## Technical Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.14 |
| Web scraping | requests, BeautifulSoup4 |
| PDF processing | pymupdf 1.27.1 |
| OCR | EasyOCR (GPU) |
| Image processing | numpy, OpenCV |
| Storage | SQLite |
| NLP / NER | spaCy |
| Analysis | pandas |
| Hardware | RTX 2060 Super (CUDA) |
| Environment | venv, Fedora Linux |

---

## Project Structure

```
foia-scraper/
├── data/
│   ├── raw/                          # 1,264 PDFs (gitignored — ~5.4 GB)
│   ├── processed-data/               # SQLite database (gitignored — ~160MB)
│   └── metadata/
│       └── scraped_docs.csv          # Metadata for all documents (1,281 rows)
├── notebooks/
│   ├── 00_minor_updates.ipynb        # Data housekeeping (metadata CSV merging etc.)
│   ├── 01_pdf_extractions.ipynb      # Extraction method comparison and testing
│   └── 02_text_analysis.ipynb        # PII detection and analysis (in progress)
├── src/
│   ├── config.py
│   ├── scraper.py
│   └── pdf_processing.py
├── main.py
└── requirements.txt
```

---

## Reproducing the Dataset

Raw PDFs are not included due to size (~5.4 GB). To reproduce:

```bash
git clone https://github.com/sbousfield/foia-scraper.git
cd foia-scraper
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

> **Note:** The site geo-filters non-Australian IP addresses.

---

## Limitations

- Geographic restriction — site requires an Australian IP address
- Scope — currently limited to the Department of Health disclosure log
- Point in time — snapshot of the disclosure log at time of scraping
- OCR quality varies on heavily scanned or low-resolution documents

---

## Possible Extensions

- Extend to additional government departments for comparative redaction quality analysis
- Test the hypothesis that higher FOI request volume correlates with better redaction compliance
- Automated periodic scraping to monitor new releases over time

---

## License

MIT License — free to use, copy, and modify with attribution.

---

*README drafted with AI assistance.*
