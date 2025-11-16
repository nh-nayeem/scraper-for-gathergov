import json
import asyncio
from typing import Dict, Any, List, Optional

class MediaScraper:
    def __init__(self, input_file: str = 'data/input.json', output_file: str = 'data/output.json'):
        self.input_file = input_file
        self.output_file = output_file
        self.results = []

    def _get_scraper(self, url: str):
        if "dallastx.new.swagit.com" in url:
            from scrapers.dallastxnewswagit import DallasTxNewSwagitScraper
            return DallasTxNewSwagitScraper
        if "champds.com" in url:
            from scrapers.champds import champdsScraper
            return champdsScraper
        if "cityofventura.ca.gov" in url:
            from scrapers.cityofventura import cityofventuraScraper
            return cityofventuraScraper
        if "video.ibm.com" in url:
            from scrapers.ibm import ibmScraper
            return ibmScraper
        return None

    async def process_url(self, url: str, url_type: str) -> Dict[str, Any]:
        """Delegate scraping of a URL to the appropriate scraper module."""
        scraper_cls = self._get_scraper(url)

        if scraper_cls is None:
            print(f"No scraper available for URL: {url}")
            return None

        try:
            scraper = scraper_cls()
            return await scraper.scrape(url, url_type)
        except Exception as exc:  # noqa: BLE001
            print(f"Error processing {url}: {exc}")
            return None

    async def run(self):
        # Read input file
        with open(self.input_file, 'r') as f:
            data = json.load(f)
        
        # Process each URL concurrently and collect results
        for item in data:
            url = item['url']
            url_type = item.get('type', 'N/A')
            result = await self.process_url(url, url_type)
            if result:
                self.results.append(result)

        # Save results to output file
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\nResults saved to {self.output_file}")

async def main():
    scraper = MediaScraper()
    await scraper.run()

if __name__ == '__main__':
    asyncio.run(main())
