from typing import List, Dict, Any
import json
import importlib.util
import sys
from pathlib import Path

class MeetingScraper:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.results = []
        
    def _get_scraper_module(self, base_url: str):
        """Dynamically import the appropriate scraper module based on the URL."""
        if 'cityofventura' in base_url:
            from scrapers.cityofventura import CityOfVenturaScraper
            return CityOfVenturaScraper
        
        if 'facebook' in base_url:
            from scrapers.facebook import FacebookScraper
            return FacebookScraper
        
        if 'lansdale' in base_url:
            from scrapers.lansdale import LansdaleScraper
            return LansdaleScraper
        
        if 'bethlehem' in base_url:
            from scrapers.bethlehem import BethlehemScraper
            return BethlehemScraper
        return None

    def scrape(self) -> List[Dict[str, Any]]:
        start_date = self.config["start_date"]
        end_date = self.config["end_date"]
        
        for base_url in self.config["base_urls"]:
            result = {
                "base_url": base_url,
                "medias": []
            }
            
            # Get the appropriate scraper module
            scraper_module = self._get_scraper_module(base_url)
            
            if scraper_module is None:
                print(f"No specific scraper found for {base_url}, using default scraper")
                continue
                
            try:
                # Call the scrape_url method directly - Playwright management is now inside each scraper
                meetings_data = scraper_module.scrape_url(
                    base_url=base_url,
                    start_date=start_date,
                    end_date=end_date
                )
                result["medias"] = meetings_data
                
                if result["medias"]:  # Only add if we found meetings
                    self.results.append(result)
                    
            except Exception as e:
                print(f"Error processing {base_url}: {e}")
                continue
            
        return self.results

def load_config(file_path: str) -> Dict[str, Any]:
    """Load configuration from a JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)

def save_results(results: List[Dict[str, Any]], file_path: str) -> None:
    """Save results to a JSON file."""
    with open(file_path, 'w') as f:
        json.dump(results, f, indent=2)

def main():
    # Load configuration
    config = load_config('Data/input.json')
    
    # Run the scraper
    scraper = MeetingScraper(config)
    results = scraper.scrape()
    
    # Save results to output file with timestamp
    output_file = f'data/output.json'
    save_results(results, output_file)
    
    print(f"\nScraping complete. Results saved to {output_file}")
    print(f"Total meetings found: {sum(len(result['medias']) for result in results)}")

if __name__ == "__main__":
    main()