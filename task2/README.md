# GatherGov Web Scraper

This project contains a web scraper to filter and extract valid downloadable URLs from a list of URLs.

## Input/Output Data

### Input
- The scraper reads input data from the `data/input.json` file.
- The input file should contain the necessary configuration and parameters for the scraping process.

### Output
- The scraped data is saved to `data/output.json`.
- The output file contains the list of valid downloadable URLs.

## How to Run

To run the scraper, use the following command:

```bash
python scraper.py
```

## Requirements
- Python 3.7+
- yt-dlp
- ffmpeg
- javascript runtime (Node/Deno)
- pip (Python package manager)

## Setup
1. Install the required Python packages:
   ```bash
   pip install yt-dlp
   ```

2. Run the scraper using the command mentioned above.