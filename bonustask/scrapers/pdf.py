import asyncio
import random
import re
import json
from datetime import datetime
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional
from pathlib import Path

class PdfScraper:
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
                headless=False,
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
                
                # Wait for either content or timeout
                try:
                    await page.wait_for_selector('a[href*=".pdf"]', timeout=15000)
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
                
                # Save HTML content to debug file
                debug_dir = Path("debug")
                debug_dir.mkdir(exist_ok=True)
                with open(debug_dir / "element.html", 'w', encoding='utf-8') as f:
                    f.write(content)
                
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
        
        # Preprocess: remove ordinal suffixes (st, nd, rd, th)
        cleaned_date = re.sub(r'(\d+)(st|nd|rd|th)\b', r'\1', date_str)
        
        # Common date patterns to match
        patterns = [
            # MM/DD/YYYY, M/D/YYYY
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',
            # MM-DD-YY, M-D-YY (2-digit year)
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{2})',
            # MM.DD.YYYY, M.D.YYYY (dot separators)
            r'(\d{1,2})\.(\d{1,2})\.(\d{4})',
            # MM.DD.YY, M.D.YY (2-digit year with dots)
            r'(\d{1,2})\.(\d{1,2})\.(\d{2})',
            # MMDDYY (6-digit without separators)
            r'(\d{2})(\d{2})(\d{2})',
            # Month DD, YYYY (with optional space and ordinal suffixes removed)
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s*(\d{1,2}),?\s+(\d{4})',
            # DD Month YYYY
            r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})',
            # YYYY-MM-DD, YYYY/MM/DD
            r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, cleaned_date)
            if match:
                groups = match.groups()
                
                try:
                    if len(groups) == 3:
                        # Determine the order based on pattern
                        if pattern.startswith(r'(\d{4})'):  # YYYY-MM-DD format
                            year, month, day = groups
                        elif pattern.startswith(r'(January|February|March|April|May|June|July|August|September|October|November|December)'):  # Month DD, YYYY
                            month_str, day, year = groups
                            month = datetime.strptime(month_str[:3], '%b').month
                        elif pattern.startswith(r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)'):  # DD Month YYYY
                            day, month_str, year = groups
                            month = datetime.strptime(month_str[:3], '%b').month
                        else:  # MM/DD/YYYY or MM-DD-YY format
                            month, day, year = groups
                            
                            # Handle 2-digit years (convert to 4-digit)
                            if len(year) == 2:
                                # Assume 20xx for years 00-99, could be made smarter
                                year = '20' + year
                        
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
    def _determine_document_type(text: str) -> str:
        """Determine if PDF is minutes or agenda based on text content."""
        if not text:
            return "unknown"
        
        text_lower = text.lower()
        
        # Check for minutes keywords
        minutes_keywords = ['minutes', 'minute', 'meeting minutes', 'meeting minute']
        for keyword in minutes_keywords:
            if keyword in text_lower:
                return "minutes"
        
        # Check for agenda keywords
        agenda_keywords = ['agenda', 'agendas']
        for keyword in agenda_keywords:
            if keyword in text_lower:
                return "agenda"
        
        # Default to unknown if no specific keywords found
        return "unknown"
    
    @staticmethod
    def _extract_base_identifier(filename: str, document_type: str) -> str:
        """Extract base identifier from filename by removing document type and common suffixes."""
        # Convert to lowercase for consistent matching
        filename_lower = filename.lower()
        
        # Remove document type keywords
        for keyword in ['agenda', 'minutes', 'minute']:
            filename_lower = filename_lower.replace(keyword, '')
        
        # Remove common suffixes
        suffixes_to_remove = ['-draft', '-combined', '-packet', '-1', '-2', '-final']
        for suffix in suffixes_to_remove:
            filename_lower = filename_lower.replace(suffix, '')
        
        # Clean up multiple hyphens and spaces
        filename_lower = re.sub(r'-+', '-', filename_lower)
        filename_lower = filename_lower.strip('-')
        
        return filename_lower
    
    @staticmethod
    def _clean_filename_for_lcs(filename: str) -> str:
        """Clean filename for LCS calculation by removing dates, extensions, and document types."""
        # Convert to lowercase for consistent matching
        filename_lower = filename.lower()
        
        # Remove file extension
        filename_lower = re.sub(r'\.pdf$', '', filename_lower)
        
        # Remove date patterns (MM-DD-YY, MM-DD-YYYY, etc.)
        filename_lower = re.sub(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', '', filename_lower)
        
        # Remove document type keywords
        for keyword in ['agenda', 'minutes', 'minute']:
            filename_lower = filename_lower.replace(keyword, '')
        
        # Remove common suffixes
        suffixes_to_remove = ['-draft', '-combined', '-packet', '-1', '-2', '-final', '-corrected', 'full']
        for suffix in suffixes_to_remove:
            filename_lower = filename_lower.replace(suffix, '')
        
        # Clean up multiple hyphens and spaces
        filename_lower = re.sub(r'-+', '-', filename_lower)
        filename_lower = filename_lower.strip('-')
        filename_lower = filename_lower.strip()
        
        return filename_lower
    
    @staticmethod
    def _longest_common_substring(s1: str, s2: str) -> str:
        """Calculate longest common substring between two strings using dynamic programming."""
        if not s1 or not s2:
            return ""
        
        m, n = len(s1), len(s2)
        # Create DP table
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        # Variables to track longest substring
        max_length = 0
        end_pos_s1 = 0
        
        # Fill DP table
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i - 1] == s2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                    if dp[i][j] > max_length:
                        max_length = dp[i][j]
                        end_pos_s1 = i
                else:
                    dp[i][j] = 0
        
        # Extract longest common substring
        if max_length >= 8:
            return s1[end_pos_s1 - max_length:end_pos_s1]
        else:
            return ""
    
    @staticmethod
    def _merge_meetings_by_date_and_identifier(meetings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge meetings that belong to the same meeting based on date and filename identifier."""
        if not meetings:
            return []
        
        # Group meetings by date
        meetings_by_date = {}
        for meeting in meetings:
            date = meeting.get("date")
            if date:
                if date not in meetings_by_date:
                    meetings_by_date[date] = []
                meetings_by_date[date].append(meeting)
        
        merged_meetings = []
        
        for date, date_meetings in meetings_by_date.items():
            # Group by base identifier within each date
            meetings_by_identifier = {}
            
            for meeting in date_meetings:
                # Find the PDF URL and extract identifier
                pdf_url = None
                for key, value in meeting.items():
                    if key in ['agenda', 'minutes'] and isinstance(value, str) and value.endswith('.pdf'):
                        pdf_url = value
                        break
                
                if pdf_url:
                    filename = pdf_url.split('/')[-1]
                    document_type = None
                    for key in meeting.keys():
                        if key in ['agenda', 'minutes']:
                            document_type = key
                            break
                    
                    base_identifier = PdfScraper._extract_base_identifier(filename, document_type)
                    
                    if base_identifier not in meetings_by_identifier:
                        meetings_by_identifier[base_identifier] = {}
                    
                    # Merge this meeting into the identifier group
                    for key, value in meeting.items():
                        if key in ['agenda', 'minutes']:
                            meetings_by_identifier[base_identifier][key] = value
                        elif key not in meetings_by_identifier[base_identifier]:
                            meetings_by_identifier[base_identifier][key] = value
            
            # Convert grouped meetings back to list
            for merged_meeting in meetings_by_identifier.values():
                merged_meetings.append(merged_meeting)
        
        return merged_meetings
    
    @staticmethod
    def _merge_meetings_by_date_and_lcs(meetings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge meetings that belong to the same meeting based on date and longest common substring."""
        print(f"DEBUG: _merge_meetings_by_date_and_lcs called with {len(meetings)} meetings")
        
        if not meetings:
            print("DEBUG: No meetings provided, returning empty list")
            return []
        
        # Group meetings by date
        meetings_by_date = {}
        for meeting in meetings:
            date = meeting.get("date")
            print(f"DEBUG: Processing meeting with date: {date}, keys: {list(meeting.keys())}")
            if date:
                if date not in meetings_by_date:
                    meetings_by_date[date] = []
                meetings_by_date[date].append(meeting)
        
        print(f"DEBUG: Grouped meetings by date: {list(meetings_by_date.keys())}")
        
        merged_meetings = []
        
        for date, date_meetings in meetings_by_date.items():
            print(f"DEBUG: Processing {len(date_meetings)} meetings for date {date}")
            # Find PDF URLs and clean filenames for this date
            meeting_data = []
            for meeting in date_meetings:
                pdf_url = None
                document_type = None
                for key, value in meeting.items():
                    if key in ['agenda', 'minutes', 'unknown'] and isinstance(value, str) and value.endswith('.pdf'):
                        pdf_url = value
                        document_type = key
                        break
                
                if pdf_url:
                    filename = pdf_url.split('/')[-1]
                    cleaned_filename = PdfScraper._clean_filename_for_lcs(filename)
                    meeting_data.append({
                        'meeting': meeting,
                        'pdf_url': pdf_url,
                        'document_type': document_type,
                        'cleaned_filename': cleaned_filename,
                        'original_filename': filename
                    })
            
            print(f"DEBUG: Found {len(meeting_data)} meetings with PDF URLs for date {date}")
            
            # If no meetings with proper document types, just add them as-is
            if not meeting_data:
                print(f"DEBUG: No meetings with PDF URLs found for date {date}, adding original meetings")
                merged_meetings.extend(date_meetings)
                continue
            
            # Merge meetings based on LCS
            used_indices = set()
            for i, meeting1 in enumerate(meeting_data):
                if i in used_indices:
                    continue
                
                merged_meeting = meeting1['meeting'].copy()
                
                # Try to find matching meetings
                for j, meeting2 in enumerate(meeting_data):
                    if i == j or j in used_indices:
                        continue
                    
                    # Calculate LCS between cleaned filenames
                    lcs = PdfScraper._longest_common_substring(
                        meeting1['cleaned_filename'], 
                        meeting2['cleaned_filename']
                    )
                    
                    # If LCS length >= 8, merge the meetings
                    if len(lcs) >= 8:
                        # Add the other document type to merged meeting
                        if meeting2['document_type'] not in merged_meeting:
                            merged_meeting[meeting2['document_type']] = meeting2['pdf_url']
                        
                        # Merge titles if both exist
                        title1 = merged_meeting.get('title', '')
                        title2 = meeting2['meeting'].get('title', '')
                        
                        if title1 and title2 and title1 != title2:
                            # Combine titles, remove duplicates and clean up
                            title_parts = []
                            if title1:
                                title_parts.append(title1)
                            if title2 and title2 not in title_parts:
                                title_parts.append(title2)
                            
                            # Create combined title like "Agenda, Minutes"
                            merged_meeting['title'] = ', '.join(title_parts)
                        elif title2 and not title1:
                            merged_meeting['title'] = title2
                        
                        used_indices.add(j)
                
                used_indices.add(i)
                merged_meetings.append(merged_meeting)
        
        return merged_meetings
    
    @staticmethod
    def _extract_pdf_data(html_content: str, base_url: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Extract meeting data from PDF links using BeautifulSoup."""
        soup = BeautifulSoup(html_content, 'html.parser')
        meetings = []
        
        # Find all links containing PDF
        pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.IGNORECASE))
        
        print(f"DEBUG: Found {len(pdf_links)} PDF links")
        for i, link in enumerate(pdf_links[:5]):  # Show first 5 for debugging
            print(f"DEBUG: PDF {i+1}: href={link.get('href')}, text={link.get_text(strip=True)}")
        
        if not pdf_links:
            return None
        
        for link in pdf_links:
            meeting = {}
            meeting_date = None
            
            # Get PDF URL
            href = link.get('href')
            if not href:
                continue
            
            pdf_url = PdfScraper._normalize_url(href, base_url)
            
            # Get text content for date and document type extraction
            link_text = link.get_text(strip=True)
            
            # Try to extract date from link text first
            parsed_date = PdfScraper._parse_date(link_text)
            if parsed_date:
                meeting_date = parsed_date
            
            # Also try to extract date from filename
            if not meeting_date:
                filename = pdf_url.split('/')[-1]
                filename_date = PdfScraper._parse_date(filename)
                if filename_date:
                    meeting_date = filename_date
            
            # Determine document type
            document_type = PdfScraper._determine_document_type(link_text)
            
            # print(f"DEBUG: Processing PDF - href: {href}, text: {link_text}, date: {meeting_date}, type: {document_type}")
            
            # If date extraction successful and date is within range
            if meeting_date and PdfScraper._is_date_in_range(meeting_date, start_date, end_date):
                meeting["date"] = meeting_date
                meeting[document_type] = pdf_url
                
                # Add additional info if available
                if link_text:
                    meeting["title"] = link_text
                
                meetings.append(meeting)
                print(f"DEBUG: Added meeting: {meeting}")
        
        # print(f"DEBUG: Total meetings found: {len(meetings)}")
        
        # Merge meetings that belong to the same meeting using LCS
        merged_meetings = PdfScraper._merge_meetings_by_date_and_lcs(meetings)
        
        return merged_meetings if merged_meetings else None
    
    @staticmethod
    def try_scrape(url: str, start_date: str, end_date: str) -> Optional[List[Dict[str, Any]]]:
        """Try to scrape meeting data by collecting meeting agendas and minutes from PDF files.
        
        Args:
            url: The URL to scrape
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Meeting data if successful, None if unsuccessful
        """
        try:
            # Run async function to get page content
            html_content = asyncio.run(PdfScraper._load_page_with_playwright(url))
            
            if html_content is None:
                return None
            
            # Extract PDF data with date filtering
            meetings = PdfScraper._extract_pdf_data(html_content, url, start_date, end_date)
            
            if meetings is None:
                return None
            
            return meetings
            
        except Exception as e:
            print(f"Error in PdfScraper for {url}: {e}")
            return None