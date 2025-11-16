import json
import asyncio
import subprocess
import requests
import logging
from pathlib import Path
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import mimetypes

# File extensions for expected types
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm', '.m4v', '.mpg', '.mpeg'}
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a', '.wma', '.opus'}
DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.rtf', '.odt'}

class MediaScraper:
    def __init__(self, input_file='data/input.json', output_file='data/output.json'):
        self.input_file = input_file
        self.output_file = output_file
        self.results = []
        
    def is_downloadable_extension(self, url, expected_type=None):
        """Check if URL has a downloadable file extension"""
        parsed = urlparse(url.lower())
        path = parsed.path
        ext = Path(path).suffix
        
        if expected_type == 'video':
            return ext in VIDEO_EXTENSIONS
        elif expected_type == 'audio':
            return ext in AUDIO_EXTENSIONS
        elif expected_type == 'document':
            return ext in DOCUMENT_EXTENSIONS
        else:
            return ext in (VIDEO_EXTENSIONS | AUDIO_EXTENSIONS | DOCUMENT_EXTENSIONS)
    
    def check_with_requests(self, url):
        """Check if URL is downloadable with requests"""
        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()
                
                # Check content type
                if any(t in content_type for t in ['video', 'audio', 'pdf', 'document', 'application/pdf', 
                                                     'application/msword', 'application/vnd.ms-excel',
                                                     'application/vnd.openxmlformats']):
                    return True, content_type
                
                # Check content disposition for downloads
                content_disposition = response.headers.get('content-disposition', '')
                if 'attachment' in content_disposition.lower():
                    return True, content_type
                    
        except Exception as e:
            print(f"  Request check failed: {str(e)}")
        return False, None
    
    def check_with_ytdlp(self, url):
        """Check if URL is downloadable with yt-dlp"""
        try:
            result = subprocess.run(
                ['yt-dlp', '--dump-json', '--no-warnings', '--skip-download', url],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout:
                info = json.loads(result.stdout)
                return True, info.get('url') or info.get('webpage_url')
        except subprocess.TimeoutExpired:
            print(f"  yt-dlp check timed out")
        except FileNotFoundError:
            print(f"  yt-dlp not found, skipping yt-dlp check")
        except Exception as e:
            print(f"  yt-dlp check failed: {str(e)}")
        return False, None
    
    async def extract_links_from_page(self, page, base_url):
        """Extract all potential media links from the page"""
        links = []
        
        # Get page content
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Find all links
        for tag in soup.find_all(['a', 'source', 'video', 'audio', 'iframe', 'embed']):
            url = None
            
            if tag.name == 'a':
                url = tag.get('href')
            elif tag.name in ['source', 'video', 'audio']:
                url = tag.get('src')
            elif tag.name in ['iframe', 'embed']:
                url = tag.get('src')
            
            if url:
                # Make absolute URL
                absolute_url = urljoin(base_url, url)
                if absolute_url not in links and absolute_url.startswith(('http://', 'https://')):
                    links.append(absolute_url)
        
        return links
    
    async def process_url(self, url_data):
        """Process a single URL from input"""
        url = url_data['url']
        expected_type = url_data.get('type', 'unknown')
        
        print(f"\n{'='*80}")
        print(f"Processing: {url}")
        print(f"Expected type: {expected_type}")
        print(f"{'='*80}")
        
        result = {
            'source_url': url,
            'expected_type': expected_type,
            'downloadable_links': []
        }
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()
            
            try:
                # Navigate to the page
                print(f"Loading page...")
                await page.goto(url, wait_until='networkidle', timeout=30000)
                await page.wait_for_timeout(2000)  # Wait for dynamic content
                
                # Extract all links from the page
                print(f"Extracting links from page...")
                links = await self.extract_links_from_page(page, url)
                print(f"Found {len(links)} links on page")
                
                # Check each link
                for link in links:
                    print(f"\n  Checking: {link[:100]}...")
                    
                    # Check if it has a downloadable extension
                    if self.is_downloadable_extension(link, expected_type):
                        print(f"  ✓ Has downloadable extension")
                        
                        # Verify with requests
                        is_downloadable, content_type = self.check_with_requests(link)
                        if is_downloadable:
                            print(f"  ✓ Confirmed downloadable via requests (type: {content_type})")
                            result['downloadable_links'].append({
                                'url': link,
                                'method': 'requests',
                                'content_type': content_type
                            })
                            continue
                    
                    # Try yt-dlp
                    is_ytdlp, extracted_url = self.check_with_ytdlp(link)
                    if is_ytdlp:
                        print(f"  ✓ Downloadable via yt-dlp")
                        result['downloadable_links'].append({
                            'url': link,
                            'method': 'yt-dlp',
                            'extracted_url': extracted_url
                        })
                        continue
                    
                    # Try requests for any link
                    is_downloadable, content_type = self.check_with_requests(link)
                    if is_downloadable:
                        print(f"  ✓ Downloadable via requests (type: {content_type})")
                        result['downloadable_links'].append({
                            'url': link,
                            'method': 'requests',
                            'content_type': content_type
                        })
                
                # If no links found on page, try the source URL itself
                if not result['downloadable_links']:
                    print(f"\nNo downloadable links found on page. Checking source URL itself...")
                    
                    # Try yt-dlp on source URL
                    is_ytdlp, extracted_url = self.check_with_ytdlp(url)
                    if is_ytdlp:
                        print(f"  ✓ Source URL downloadable via yt-dlp")
                        result['downloadable_links'].append({
                            'url': url,
                            'method': 'yt-dlp',
                            'extracted_url': extracted_url
                        })
                    else:
                        # Try requests on source URL
                        is_downloadable, content_type = self.check_with_requests(url)
                        if is_downloadable:
                            print(f"  ✓ Source URL downloadable via requests (type: {content_type})")
                            result['downloadable_links'].append({
                                'url': url,
                                'method': 'requests',
                                'content_type': content_type
                            })
                
            except Exception as e:
                print(f"Error processing {url}: {str(e)}")
                result['error'] = str(e)
            
            finally:
                await browser.close()
        
        # Summary
        print(f"\n{'='*80}")
        print(f"Summary for {url}")
        print(f"Found {len(result['downloadable_links'])} downloadable link(s)")
        for i, link in enumerate(result['downloadable_links'], 1):
            print(f"  {i}. {link['url'][:80]}... (method: {link['method']})")
        print(f"{'='*80}\n")
        
        return result
    
    async def run(self):
        """Main execution method"""
        # Read input file
        print(f"Reading input from {self.input_file}...")
        with open(self.input_file, 'r') as f:
            input_data = json.load(f)
        
        print(f"Found {len(input_data)} URLs to process\n")
        
        # Process each URL
        for url_data in input_data:
            result = await self.process_url(url_data)
            self.results.append(result)
        
        # Write output file
        print(f"\nWriting results to {self.output_file}...")
        with open(self.output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n{'='*80}")
        print(f"COMPLETE!")
        print(f"Processed {len(self.results)} URLs")
        print(f"Results saved to {self.output_file}")
        print(f"{'='*80}")

async def main():
    scraper = MediaScraper()
    await scraper.run()

if __name__ == '__main__':
    asyncio.run(main())
