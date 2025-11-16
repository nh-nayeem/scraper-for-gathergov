import json
import asyncio
import aiohttp
import logging
from pathlib import Path
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import mimetypes
from typing import Set, Dict, Any, List, Optional

# File extensions for expected types
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm', '.m4v', '.mpg', '.mpeg'}
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a', '.wma', '.opus'}
DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.rtf', '.odt'}

class MediaScraper:
    def __init__(self, input_file='data/input.json', output_file='data/output.json'):
        self.input_file = input_file
        self.output_file = output_file
        self.results = []
    
    async def process_url(self, url, url_type):
        """
        Process a single URL with its type
        
        Args:
            url (str): The URL to process
            url_type (str): The type of content expected
            
        Returns:
            dict: Dictionary containing processing results
        """
        result = {
            'url': url,
            'type': url_type,
            'status': 'pending',
            'links': set(),  # Using set to store unique links
            'error': None
        }
        
        # Launch Playwright browser
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = await context.new_page()
                
                # Navigate to the URL
                print(f"Loading {url}...")
                response = await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                
                # Wait for the page to be fully loaded
                await page.wait_for_load_state('networkidle')
                
                # Get the page content
                html_content = await page.content()
                
                # Parse with BeautifulSoup
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Extract all unique links
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    # Skip empty or anchor links
                    if not href or href.startswith('#'):
                        continue
                    full_url = urljoin(url, href)
                    result['links'].add(full_url)  # Using set to ensure uniqueness
                
                result['status'] = 'completed'
                print(f"Successfully processed {url}")
                
            except Exception as e:
                error_msg = f"Error processing {url}: {str(e)}"
                print(error_msg)
                result['status'] = 'error'
                result['error'] = str(e)
                
            finally:
                # Clean up
                if 'browser' in locals():
                    await browser.close()
        
        # Convert set to list for JSON serialization and sort for consistent output
        result['links'] = list(sorted(result['links']))
        return result
    
    async def run(self):
        # Read input file
        with open(self.input_file, 'r') as f:
            data = json.load(f)
        
        # Process each URL and collect results
        results = []
        for item in data:
            url = item['url']
            url_type = item.get('type', 'N/A')
            result = await self.process_url(url, url_type)
            results.append(result)
        
        # Save results to output file
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\nResults saved to {self.output_file}")

async def main():
    scraper = MediaScraper()
    await scraper.run()

if __name__ == '__main__':
    asyncio.run(main())
