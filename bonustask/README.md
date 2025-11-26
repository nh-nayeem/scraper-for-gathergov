# GatherGov Web Scraper

This project contains a web scraper built with Playwright and beautifulSoup to extract data from the multiple websites.

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

To run the scraper with browser head , use the following command:

```bash
python scraper.py --head
```

## Requirements
- Python 3.7+
- Playwright
- playwright-stealth
- BeautifulSoup4
- pip (Python package manager)

## Setup
1. Install the required Python packages:
   ```bash
   pip install playwright beautifulsoup4 playwright-stealth
   ```

2. Install browser binaries for Playwright:
   ```bash
   playwright install
   ```
   This will download the necessary browser binaries for Chromium, Firefox, and WebKit.
3. Run the scraper using the command mentioned above.