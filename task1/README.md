# GatherGov Web Scraper

This project contains a web scraper built with Playwright to extract data from the GatherGov website.

## Input/Output Data

### Input
- The scraper reads input data from the `data/input.json` file.
- The input file should contain the necessary configuration and parameters for the scraping process.

### Output
- The scraped data is saved to `data/output.json`.
- The output file contains structured data extracted from the target website.

## How to Run

To run the scraper, use the following command:

```bash
python scraper.py
```

## Requirements
- Python 3.7+
- Playwright
- BeautifulSoup4
- pip (Python package manager)

## Setup
1. Install the required Python packages:
   ```bash
   pip install playwright beautifulsoup4
   ```

2. Install browser binaries for Playwright:
   ```bash
   playwright install
   ```
   This will download the necessary browser binaries for Chromium, Firefox, and WebKit.
2. Run the scraper using the command mentioned above.