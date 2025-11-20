import asyncio
import random
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional


class TableScraper:
    @staticmethod
    async def _load_page_with_playwright(url: str) -> Optional[str]:
        """Load page content using Playwright with stealth mode."""
        stealth = Stealth(
            navigator_languages_override=("en-US", "en"),
            navigator_platform="Win32",
            init_scripts_only=True
        )
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
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
                return content
                
            except Exception as e:
                print(f"Error loading {url}: {e}")
                return None
            finally:
                await browser.close()
    
    @staticmethod
    def _normalize_url(url: str, base_url: str) -> str:
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
    
    @staticmethod
    def _parse_date(date_str: str) -> Optional[str]:
        """Parse date string in various formats and return YYYY-MM-DD format."""
        if not date_str:
            return None
        
        # Common date patterns to match
        patterns = [
            # MM/DD/YYYY, M/D/YYYY
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',
            # Month DD, YYYY
            r'([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})',
            # DD Month YYYY
            r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})',
            # YYYY-MM-DD, YYYY/MM/DD
            r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, date_str)
            if match:
                groups = match.groups()
                
                try:
                    if len(groups) == 3:
                        # Determine the order based on pattern
                        if pattern.startswith(r'(\d{4})'):  # YYYY-MM-DD format
                            year, month, day = groups
                        elif pattern.startswith(r'([A-Za-z]+)'):  # Month DD, YYYY
                            month_str, day, year = groups
                            month = datetime.strptime(month_str[:3], '%b').month
                        elif pattern.startswith(r'(\d{1,2})\s+([A-Za-z]+)'):  # DD Month YYYY
                            day, month_str, year = groups
                            month = datetime.strptime(month_str[:3], '%b').month
                        else:  # MM/DD/YYYY format
                            month, day, year = groups
                        
                        # Create date object and format
                        date_obj = datetime(int(year), int(month), int(day))
                        return date_obj.strftime('%Y-%m-%d')
                        
                except (ValueError, AttributeError):
                    continue
        
        return None
    
    @staticmethod
    def _is_date_in_range(meeting_date: str, start_date: str, end_date: str) -> bool:
        """Check if meeting date is within the specified range."""
        if not meeting_date:
            return True  # If no date found, include by default
        
        try:
            meeting_dt = datetime.strptime(meeting_date, '%Y-%m-%d')
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            return start_dt <= meeting_dt <= end_dt
        except ValueError:
            return True  # If date parsing fails, include by default
    
    @staticmethod
    def _has_media_data(meeting: Dict[str, Any]) -> bool:
        """Check if meeting has at least one media data (non-empty value that's a URL or file)."""
        for key, value in meeting.items():
            if value and isinstance(value, str):
                # Check if it's a URL or file path (contains .pdf, .doc, etc.)
                if (value.startswith(('http://', 'https://', '/')) or 
                    any(value.lower().endswith(ext) for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.mp3', '.mp4', '.wav'])):
                    return True
        return False
    
    @staticmethod
    def _normalize_key(cell_text: str) -> str:
        """Normalize cell text to standard key from predefined keywords."""
        if not cell_text:
            return cell_text
        
        # Convert to lowercase for case-insensitive matching
        text_lower = cell_text.lower()
        
        # Define keyword mappings in order of priority
        keyword_mappings = [
            # Agenda keywords
            (['agenda'], 'agenda'),
            # Minutes keywords  
            (['minutes'], 'minutes'),
            # Recording/video keywords
            (['recording', 'video', 'audio'], 'recording'),
            # Packet/document keywords
            (['packet', 'agenda packet', 'agenda-packet'], 'agenda_packet'),
            # Notice keywords
            (['notice', 'cancellation', 'cancelled'], 'notice'),
            # Special meeting keywords
            (['special meeting', 'special'], 'special_meeting'),
            # Regular meeting keywords
            (['regular meeting', 'regular'], 'regular_meeting'),
            # Workshop keywords
            (['workshop', 'community workshop'], 'workshop'),
            # Town hall keywords
            (['town hall', 'community meet and greet'], 'town_hall'),
            # Correspondence keywords
            (['correspondence', 'non-agenda'], 'correspondence'),
            # Attachment keywords
            (['attachment', 'exhibit', 'appendix'], 'attachment'),
            # Material keywords
            (['material', 'updated material', 'additional material'], 'material'),
            # Presentation keywords
            (['presentation', 'powerpoint'], 'presentation'),
            # Report keywords
            (['report', 'staff report'], 'report'),
            # Plan keywords
            (['plan', 'project plan'], 'plan'),
            # Other common meeting items
            (['summary', 'addendum', 'update'], 'other'),
        ]
        
        # Check for keyword matches
        for keywords, standard_key in keyword_mappings:
            for keyword in keywords:
                if keyword in text_lower:
                    return standard_key
        
        # If no keyword matches, return original text
        return cell_text
    
    @staticmethod
    def _extract_table_data(html_content: str, base_url: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Extract meeting data from table rows using BeautifulSoup."""
        soup = BeautifulSoup(html_content, 'html.parser')
        meetings = []
        
        # Find all table rows
        tr_elements = soup.find_all('tr')
        
        if not tr_elements:
            return None
        
        for tr in tr_elements:
            meeting = {}
            meeting_date = None
            
            # Find all cells in the row (td and th)
            cells = tr.find_all(['td', 'th'])
            
            if not cells:
                continue
            
            # Extract data from each cell
            for cell in cells:
                # Get cell text as key (cleaned)
                cell_text = cell.get_text(strip=True)
                if not cell_text:
                    continue
                
                # Check if this cell contains date information
                parsed_date = TableScraper._parse_date(cell_text)
                if parsed_date:
                    meeting_date = parsed_date
                    # Use "date" as key and the actual parsed date as value
                    key = "date"
                    value = parsed_date
                    meeting[key] = value
                else:
                    # Use normalized key for non-date data
                    key = TableScraper._normalize_key(cell_text)
                    
                    # Find links in the cell
                    links = cell.find_all('a')
                    if links:
                        # Use the first link's href as value
                        href = links[0].get('href')
                        if href:
                            # Normalize the URL
                            normalized_url = TableScraper._normalize_url(href, base_url)
                            meeting[key] = normalized_url
                        else:
                            # Link exists but no href - set empty value
                            meeting[key] = ""
                    else:
                        # If no link, use cell text as value
                        meeting[key] = cell_text
            
            # Only add meeting if we have some data
            if meeting:
                # Check if meeting is in date range
                if TableScraper._is_date_in_range(meeting_date, start_date, end_date):
                    # Check if meeting has at least one media data
                    if TableScraper._has_media_data(meeting):
                        meetings.append(meeting)
        
        return meetings if meetings else None
    
    @staticmethod
    def try_scrape(url: str, start_date: str, end_date: str) -> Optional[List[Dict[str, Any]]]:
        """Try to scrape meeting data using table-based approach.
        
        Args:
            url: The URL to scrape
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Meeting data if successful, None if unsuccessful
        """
        try:
            # Run async function to get page content
            html_content = asyncio.run(TableScraper._load_page_with_playwright(url))
            
            if html_content is None:
                return None
            
            # Extract table data with date filtering and media validation
            meetings = TableScraper._extract_table_data(html_content, url, start_date, end_date)
            
            if meetings is None:
                return None
            
            return meetings
            
        except Exception as e:
            print(f"Error in TableScraper for {url}: {e}")
            return None