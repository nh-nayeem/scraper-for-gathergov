import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from scrapers.table import TableScraper
from scrapers.link import LinkScraper


class MeetingScraper:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.results = []
        
        # Create debug directory and log file
        self.debug_dir = Path("debug")
        self.debug_dir.mkdir(exist_ok=True)
        self.debug_log = self.debug_dir / "logs.log"
        
        # Initialize debug log
        self._init_debug_log()
    
    def _init_debug_log(self):
        """Initialize debug log file."""
        with open(self.debug_log, 'w', encoding='utf-8') as f:
            f.write(f"Meeting Scraper Debug Log\n")
            f.write(f"========================\n")
            f.write(f"Start Date: {self.config['start_date']}\n")
            f.write(f"End Date: {self.config['end_date']}\n")
            f.write(f"Total URLs: {len(self.config['base_urls'])}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n\n")
    
    def _log_debug(self, message: str):
        """Write debug message to log file."""
        with open(self.debug_log, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().isoformat()} - {message}\n")
    
    def _scrape_url(self, url: str) -> List[Dict[str, Any]]:
        """Try different scraper modules for a URL until one succeeds."""
        start_date = self.config["start_date"]
        end_date = self.config["end_date"]
        
        self._log_debug(f"[*] Processing URL: {url}")
        
        # Try table scraper first
        try:
            self._log_debug(f"[*] Trying TableScraper for {url}")
            result = TableScraper.try_scrape(url, start_date, end_date)
            if result is not None:
                self._log_debug(f"[+] TableScraper succeeded for {url}")
                return result
            else:
                self._log_debug(f"[-] TableScraper returned None for {url}")
        except Exception as e:
            self._log_debug(f"[!] TableScraper failed for {url}: {str(e)}")
        
        # Try Link scraper if table and list scrapers failed
        try:
            self._log_debug(f"[*] Trying LinkScraper for {url}")
            result = LinkScraper.try_scrape(url, start_date, end_date)
            if result is not None:
                self._log_debug(f"[+] LinkScraper succeeded for {url}")
                return result
            else:
                self._log_debug(f"[-] LinkScraper returned None for {url}")
        except Exception as e:
            self._log_debug(f"[!] LinkScraper failed for {url}: {str(e)}")
        
        self._log_debug(f"[-] All scrapers failed for {url}")
        return []
    
    def scrape(self) -> List[Dict[str, Any]]:
        """Main scraping method."""
        for base_url in self.config["base_urls"]:
            result = {
                "base_url": base_url,
                "meetings": []
            }
            
            meetings_data = self._scrape_url(base_url)
            result["meetings"] = meetings_data
            
            if result["meetings"]:  # Only add if we found meetings
                self.results.append(result)
                self._log_debug(f"[+] Found {len(meetings_data)} meetings for {base_url}")
            else:
                self._log_debug(f"[!] No meetings found for {base_url}")
        
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
    """Main execution function."""
    # Load configuration
    config = load_config('data/input.json')
    
    # Run the scraper
    scraper = MeetingScraper(config)
    results = scraper.scrape()
    
    # Save results to output file
    output_file = 'data/output.json'
    save_results(results, output_file)
    
    print(f"\nScraping complete. Results saved to {output_file}")
    print(f"Total URLs processed: {len(config['base_urls'])}")
    print(f"Total meetings found: {sum(len(result['meetings']) for result in results)}")


if __name__ == "__main__":
    main()