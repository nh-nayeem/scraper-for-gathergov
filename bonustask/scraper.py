import json
import os
import asyncio
import random
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup

from scrapers.table import TableScraper
from scrapers.link import LinkScraper


class MeetingScraper:
    def __init__(self, config: Dict[str, Any], headless: bool = True, debug_mode: bool = False):
        self.config = config
        self.headless = headless
        self.debug_mode = debug_mode
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
    
    async def _load_page_with_playwright(self, url: str, depth: int = 0) -> Optional[str]:
        """Load page content using Playwright with stealth mode."""
        if depth > 2:  # Prevent infinite recursion
            return None

        stealth = Stealth(
            navigator_languages_override=("en-US", "en"),
            navigator_platform="Win32",
            init_scripts_only=True
        )
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-background-timer-throttling',
                    '--disable-renderer-backgrounding',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-ipc-flooding-protection',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-default-apps',
                    '--disable-popup-blocking'
                ]
            )
            
            try:
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='en-US',
                    timezone_id='America/New_York',
                    permissions=['geolocation'],
                    accept_downloads=False,
                    java_script_enabled=True,
                    ignore_https_errors=True
                )
                
                await context.set_extra_http_headers({
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'max-age=0'
                })
                
                page = await context.new_page()
                await page.set_viewport_size({"width": 1920, "height": 1080})
                
                # Navigate to URL
                await page.goto(url, timeout=45000, wait_until='domcontentloaded')
                
                # Apply stealth mode AFTER navigation
                await stealth.apply_stealth_async(page)
                
                # Wait for either tr elements or timeout
                try:
                    await page.wait_for_selector('tr', timeout=15000)
                except:
                    pass
                
                # Wait for page to be more stable
                await page.wait_for_load_state('domcontentloaded', timeout=10000)
                
                # Smart scrolling to trigger lazy loading
                try:
                    page_height = await page.evaluate("document.body.scrollHeight")
                    viewport_height = 1080
                    
                    for i in range(0, page_height, viewport_height // 2):
                        await page.evaluate(f"window.scrollTo(0, {i})")
                        await asyncio.sleep(random.uniform(0.5, 1.0))
                    
                    await page.evaluate("window.scrollTo(0, 0)")
                    await asyncio.sleep(random.uniform(0.5, 1.0))
                except Exception:
                    pass
                
                # Additional wait for JS-rendered content
                await asyncio.sleep(random.uniform(1.5, 2.5))
                
                # Get page content
                content = await page.content()
                
                # Save HTML content to debug file if debug mode is enabled
                if self.debug_mode:
                    with open(self.debug_dir / "element.html", 'w', encoding='utf-8') as f:
                        f.write(content)
                
                # Extract iframe content and merge with main content
                iframe_content = await self._extract_iframe_content(page, url, depth)
                if iframe_content:
                    content = content.replace('</body>', iframe_content + '</body>')
                
                return content
                
            except Exception as e:
                print(f"Error loading {url}: {e}")
                return None
            finally:
                await browser.close()
    
    async def _extract_iframe_content(self, page, base_url: str, depth: int = 0) -> str:
        """Extract content from iframes and return as HTML string."""
        iframe_content = ""
        
        try:
            # Get all iframe elements from the page
            iframe_elements = await page.locator('iframe').all()
            
            for iframe_element in iframe_elements:
                try:
                    # Get the src attribute from the iframe element
                    frame_url = await iframe_element.get_attribute('src')
                    
                    if frame_url:
                        # Normalize URL if relative
                        normalized_url = self._normalize_url(frame_url, base_url)
                        # Load the iframe URL content with increased depth
                        iframe_page_content = await self._load_page_with_playwright(normalized_url, depth + 1)
                        if iframe_page_content:
                            iframe_content += f'\n<!-- iframe content from {normalized_url} -->\n<div class="iframe-content">\n{iframe_page_content}\n</div>\n<!-- end iframe content -->\n'
                    else:
                        # If no src, try to get frame content directly (same-origin only)
                        try:
                            frame = await iframe_element.content_frame()
                            if frame:
                                frame_html = await frame.content()
                                if frame_html:
                                    iframe_content += f'\n<!-- iframe content -->\n<div class="iframe-content">\n{frame_html}\n</div>\n<!-- end iframe content -->\n'
                        except Exception:
                            # Cross-origin frame, skip if no src available
                            pass
                            
                except Exception as e:
                    print(f"Could not extract iframe content: {e}")
                    continue
                        
        except Exception as e:
            print(f"Error extracting iframe content: {e}")
        
        return iframe_content
    
    def _normalize_url(self, url: str, base_url: str) -> str:
        """Normalize URL - convert relative URLs to absolute."""
        if not url:
            return ""
        
        # If it's already an absolute URL, return as is
        if url.startswith(('http://', 'https://')):
            return url
        
        # If it's a relative URL starting with /, combine with base URL origin
        if url.startswith('/'):
            parsed_base = urlparse(base_url)
            return f"{parsed_base.scheme}://{parsed_base.netloc}{url}"
        
        # Otherwise, use urljoin to handle relative paths
        return urljoin(base_url, url)
    
    async def _scrape_url(self, url: str) -> List[Dict[str, Any]]:
        """Try different scraper modules for a URL until one succeeds."""
        start_date = self.config["start_date"]
        end_date = self.config["end_date"]
        
        self._log_debug(f"[*] Processing URL: {url}")
        print("Processing URL: ", url)
        # Load page content using Playwright
        try:
            html_content = await self._load_page_with_playwright(url)
            if html_content is None:
                self._log_debug(f"[!] Failed to load page content for {url}")
                return []
        except Exception as e:
            self._log_debug(f"[!] Playwright failed for {url}: {str(e)}")
            return []
        
        # Try table scraper first
        try:
            self._log_debug(f"[*] Trying TableScraper for {url}")
            result = TableScraper.try_scrape(html_content, url, start_date, end_date)
            if result is not None:
                self._log_debug(f"[+] TableScraper succeeded for {url}")
                return result
            else:
                self._log_debug(f"[-] TableScraper returned None for {url}")
        except Exception as e:
            self._log_debug(f"[!] TableScraper failed for {url}: {str(e)}")
        
        # Try Link scraper if table scraper failed
        try:
            self._log_debug(f"[*] Trying LinkScraper for {url}")
            result = LinkScraper.try_scrape(html_content, url, start_date, end_date)
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
            
            meetings_data = asyncio.run(self._scrape_url(base_url))
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
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Meeting Scraper')
    parser.add_argument('--head', action='store_true', 
                       help='Run with headless=False (show browser window)')
    parser.add_argument('--debug', action='store_true',
                       help='Run in debug mode (saves HTML to debug/element.html)')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config('data/input.json')
    
    # Determine headless mode (default True, False if --head flag is provided)
    headless = not args.head
    
    # Run the scraper
    scraper = MeetingScraper(config, headless=headless, debug_mode=args.debug)
    results = scraper.scrape()
    
    # Save results to output file
    output_file = 'data/output.json'
    save_results(results, output_file)
    
    print(f"\nScraping complete. Results saved to {output_file}")
    print(f"Total URLs processed: {len(config['base_urls'])}")
    print(f"Total meetings found: {sum(len(result['meetings']) for result in results)}")
    print(f"Headless mode: {headless}")
    print(f"Debug mode: {args.debug}")


if __name__ == "__main__":
    main()