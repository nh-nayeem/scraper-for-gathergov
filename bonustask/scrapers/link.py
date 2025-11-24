import asyncio
import random
import re
import json
import requests
from datetime import datetime
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional
from pathlib import Path

class LinkScraper:
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
                await page.goto(url, timeout=45000, wait_until='networkidle')
                
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
                await asyncio.sleep(random.uniform(3.0, 5.0))
                
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
    def _check_pdf_redirect(url: str) -> Optional[str]:
        """Check if a URL redirects to a PDF and return the final PDF URL."""
        try:
            print(f"DEBUG: Checking redirect for: {url}")
            response = requests.head(url, allow_redirects=True, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            print(f"DEBUG: Response status: {response.status_code}, final URL: {response.url}")
            
            # Check if the final URL ends with .pdf
            final_url = response.url
            if final_url.lower().endswith('.pdf'):
                print(f"DEBUG: Found PDF redirect: {url} -> {final_url}")
                return final_url
                
            return None
        except Exception as e:
            print(f"DEBUG: Error checking redirect for {url}: {e}")
            return None
    
    @staticmethod
    def _check_content_type_is_pdf(url: str) -> bool:
        """Check if the content type of a URL is PDF."""
        try:
            response = requests.head(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            content_type = response.headers.get('content-type', '').lower()
            return 'application/pdf' in content_type
        except Exception as e:
            print(f"Error checking content type for {url}: {e}")
            return False
    
    @staticmethod
    def _get_google_drive_filename(view_url: str) -> Optional[str]:
        """
        Extract the real file name from a Google Drive link
        without downloading the file.
        """
        try:
            # Extract file ID
            match = re.search(r"/file/d/([^/]+)/", view_url)
            if not match:
                return None
            
            file_id = match.group(1)
            
            # Convert to direct download URL
            download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
            
            # Make request (follow redirects)
            response = requests.get(download_url, allow_redirects=True, stream=True, timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            # Get content disposition header
            cd = response.headers.get("Content-Disposition", "")
            if not cd:
                return None
            
            # Extract filename="..."
            filename_match = re.search(r'filename="([^"]+)"', cd)
            if filename_match:
                return filename_match.group(1)
            
            return None
        except Exception as e:
            print(f"Error getting Google Drive video filename for {view_url}: {e}")
            return None

    @staticmethod
    def _is_google_drive_video(url: str) -> bool:
        """Check if a Google Drive URL points to a video file."""
        try:
            filename = LinkScraper._get_google_drive_filename(url)
            if filename:
                video_extensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv', '.m4v']
                if any(filename.lower().endswith(ext) for ext in video_extensions):
                    print(f"DEBUG: Found Google Drive video: {url} -> {filename}")
                    return True
            return False
        except Exception as e:
            print(f"Error checking Google Drive video for {url}: {e}")
            return False

    @staticmethod
    def _is_youtube_link(url: str) -> bool:
        """Check if a URL is a YouTube video link."""
        youtube_patterns = [
            r'youtube\.com/watch\?v=',
            r'youtu\.be/',
            r'm\.youtube\.com/watch\?v=',
            r'youtube\.com/embed/',
            r'youtube\.com/v/'
        ]
        return any(re.search(pattern, url.lower()) for pattern in youtube_patterns)

    @staticmethod
    def _check_video_redirect(url: str) -> Optional[str]:
        """Check if a URL redirects to a video and return the final video URL."""
        try:
            print(f"DEBUG: Checking video redirect for: {url}")
            response = requests.head(url, allow_redirects=True, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            print(f"DEBUG: Response status: {response.status_code}, final URL: {response.url}")
            
            # Check if the final URL ends with video extension
            final_url = response.url
            video_extensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv', '.m4v']
            if any(final_url.lower().endswith(ext) for ext in video_extensions):
                print(f"DEBUG: Found video redirect: {url} -> {final_url}")
                return final_url
                
            return None
        except Exception as e:
            print(f"DEBUG: Error checking video redirect for {url}: {e}")
            return None
    
    @staticmethod
    def _check_content_type_is_video(url: str) -> bool:
        """Check if the content type of a URL is video."""
        try:
            response = requests.head(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            content_type = response.headers.get('content-type', '').lower()
            video_types = [
                'video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/x-ms-wmv',
                'video/x-flv', 'video/webm', 'video/x-matroska', 'video/mpeg',
                'video/3gpp', 'video/x-m4v'
            ]
            return any(vt in content_type for vt in video_types)
        except Exception as e:
            print(f"Error checking video content type for {url}: {e}")
            return False

    @staticmethod
    def _get_youtube_title(video_url: str) -> Optional[str]:
        """Fetch YouTube video title using oEmbed API."""
        try:
            # Use YouTube's oEmbed API to get video metadata
            oembed_url = f"https://www.youtube.com/oembed?url={video_url}&format=json"
            response = requests.get(oembed_url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            if response.status_code == 200:
                data = response.json()
                title = data.get('title', '')
                print(f"DEBUG: Fetched YouTube title: {video_url} -> {title}")
                return title
            else:
                print(f"DEBUG: Failed to fetch YouTube title for {video_url}: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            print(f"DEBUG: Error fetching YouTube title for {video_url}: {e}")
            return None

    @staticmethod
    def _determine_document_type(text: str) -> str:
        """Determine if PDF is title based on text content."""
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
        
        # Check for packet keywords
        packet_keywords = ['packet', 'packets']
        for keyword in packet_keywords:
            if keyword in text_lower:
                return "packet"
        
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
    def _merge_meetings_by_date_and_matching(meetings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
            
            # For this specific site, all meetings on the same date should be merged
            # since they follow the pattern YYYY-MM-DD_[doctype]_[number].pdf
            if len(date_meetings) <= 1:
                merged_meetings.extend(date_meetings)
                continue
            
            # Create a single merged meeting for this date
            merged_meeting = {"date": date}
            titles = []
            
            for meeting in date_meetings:
                print(f"DEBUG: Merging meeting: {meeting}")
                
                # Add document types and URLs
                for key, value in meeting.items():
                    if key in ['agenda', 'minutes', 'packet', 'unknown', 'video'] and isinstance(value, str) and (value.endswith('.pdf') or value.endswith('.mp4') or value.endswith('.avi') or value.endswith('.mov') or value.endswith('.wmv') or value.endswith('.flv') or value.endswith('.webm') or value.endswith('.mkv') or value.endswith('.m4v')):
                        if key not in merged_meeting:
                            merged_meeting[key] = value
                    elif key == 'title' and value:
                        titles.append(value)
                    elif key not in merged_meeting:
                        merged_meeting[key] = value
            
            # Combine titles
            if titles:
                unique_titles = list(dict.fromkeys(titles))  # Remove duplicates while preserving order
                merged_meeting['title'] = ', '.join(unique_titles)
            
            print(f"DEBUG: Created merged meeting: {merged_meeting}")
            merged_meetings.append(merged_meeting)
        
        return merged_meetings
    
    @staticmethod
    def _extract_pdf_data(html_content: str, base_url: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Extract meeting data from PDF links using BeautifulSoup."""
        soup = BeautifulSoup(html_content, 'html.parser')
        meetings = []
        
        # Find all links - not just PDF links
        all_links = soup.find_all('a', href=True)
        
        print(f"DEBUG: Found {len(all_links)} total links")
        
        # Filter links first to avoid checking every single link
        # Look for links that might be meeting-related or already PDFs/videos
        potentially_media_links = []
        
        for link in all_links:
            href = link.get('href')
            if not href:
                continue
            link_text = link.get_text(strip=True)
            href_lower = href.lower()
            
            # Include if already PDF or video
            video_extensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv', '.m4v']
            if href_lower.endswith('.pdf') or any(href_lower.endswith(ext) for ext in video_extensions):
                potentially_media_links.append(link)
                continue
            
            # Include if YouTube link
            if LinkScraper._is_youtube_link(href):
                potentially_media_links.append(link)
                continue
            
            # Include if Google Drive link
            if 'drive.google.com' in href_lower:
                potentially_media_links.append(link)
                continue
            
            # Include if text contains date data
            if LinkScraper._parse_date(link_text):
                potentially_media_links.append(link)
                continue
                
            # Include if href contains date data
            if LinkScraper._parse_date(href):
                potentially_media_links.append(link)
        
        print(f"DEBUG: Filtered to {len(potentially_media_links)} potentially media links")
        
        valid_media_links = []
        redirect_cache = {}  # Cache to avoid duplicate requests
        google_drive_filenames = {}  # Cache Google Drive filenames for date extraction
        google_drive_video_filenames = {}  # Cache Google Drive video filenames
        youtube_titles = {}  # Cache YouTube titles for date extraction
        
        for link in potentially_media_links:
            href = link.get('href')
            if not href:
                continue
            
            link_text = link.get_text(strip=True)
            print(f"DEBUG: Checking filtered link - href: {href}, text: {link_text}")
                
            media_url = LinkScraper._normalize_url(href, base_url)
            
            # Check if it's already a PDF or video
            video_extensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv', '.m4v']
            if media_url.lower().endswith('.pdf') or any(media_url.lower().endswith(ext) for ext in video_extensions):
                valid_media_links.append(link)
                continue
            
            # Check if it's a YouTube link
            if LinkScraper._is_youtube_link(media_url):
                valid_media_links.append(link)
                continue
            
            # Check if it's a Google Drive link
            if 'drive.google.com' in media_url.lower():
                # Check for PDF
                filename = LinkScraper._get_google_drive_filename(media_url)
                if filename and filename.lower().endswith('.pdf'):
                    google_drive_filenames[media_url] = filename
                    print(f"DEBUG: Found Google Drive PDF: {media_url} -> {filename}")
                    valid_media_links.append(link)
                    continue
                
                # Check for video
                video_filename = LinkScraper._get_google_drive_filename(media_url)
                if video_filename and any(video_filename.lower().endswith(ext) for ext in video_extensions):
                    google_drive_video_filenames[media_url] = video_filename
                    print(f"DEBUG: Found Google Drive video: {media_url} -> {video_filename}")
                    valid_media_links.append(link)
                    continue
                continue
            
            # Use cache to avoid duplicate requests
            if media_url in redirect_cache:
                if redirect_cache[media_url]:
                    valid_media_links.append(link)
                    continue
            
            # If not a direct media file, try to check if it redirects to PDF or video
            redirect_pdf_url = LinkScraper._check_pdf_redirect(media_url)
            redirect_video_url = LinkScraper._check_video_redirect(media_url)
            
            if redirect_pdf_url or redirect_video_url:
                final_url = redirect_pdf_url or redirect_video_url
                redirect_cache[media_url] = final_url
                print(f"DEBUG: Found redirect to media: {media_url} -> {final_url}")
                valid_media_links.append(link)
                continue
            
            # If no redirect, check if content type is PDF or video
            if LinkScraper._check_content_type_is_pdf(media_url) or LinkScraper._check_content_type_is_video(media_url):
                print(f"DEBUG: Found media by content type: {media_url}")
                valid_media_links.append(link)
        
        print(f"DEBUG: Found {len(valid_media_links)} valid media links")
        for i, link in enumerate(valid_media_links[:5]):  # Show first 5 for debugging
            print(f"DEBUG: Media {i+1}: href={link.get('href')}, text={link.get_text(strip=True)}")
        
        if not valid_media_links:
            return None
        
        for link in valid_media_links:
            meeting = {}
            meeting_date = None
            
            # Get media URL
            href = link.get('href')
            if not href:
                continue
            
            media_url = LinkScraper._normalize_url(href, base_url)
            
            # If not a direct media file, check for redirect again to get the final URL
            video_extensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv', '.m4v']
            if not (media_url.lower().endswith('.pdf') or any(media_url.lower().endswith(ext) for ext in video_extensions)):
                redirect_url = redirect_cache.get(media_url) or LinkScraper._check_pdf_redirect(media_url) or LinkScraper._check_video_redirect(media_url)
                if redirect_url:
                    media_url = redirect_url
            
            # Get text content for date and document type extraction
            link_text = link.get_text(strip=True)
            
            # Try to extract date from link text first
            parsed_date = LinkScraper._parse_date(link_text)
            if parsed_date:
                meeting_date = parsed_date
            
            # Also try to extract date from filename
            if not meeting_date:
                filename = media_url.split('/')[-1]
                filename_date = LinkScraper._parse_date(filename)
                if filename_date:
                    meeting_date = filename_date
            
            # For Google Drive links, try to extract date from the actual filename
            if not meeting_date and media_url in google_drive_filenames:
                gd_filename = google_drive_filenames[media_url]
                gd_filename_date = LinkScraper._parse_date(gd_filename)
                if gd_filename_date:
                    meeting_date = gd_filename_date
                    print(f"DEBUG: Extracted date from Google Drive filename: {gd_filename} -> {gd_filename_date}")
            
            # For Google Drive video links, try to extract date from the video filename
            if not meeting_date and media_url in google_drive_video_filenames:
                gd_video_filename = google_drive_video_filenames[media_url]
                gd_video_filename_date = LinkScraper._parse_date(gd_video_filename)
                if gd_video_filename_date:
                    meeting_date = gd_video_filename_date
                    print(f"DEBUG: Extracted date from Google Drive video filename: {gd_video_filename} -> {gd_video_filename_date}")
            
            # For YouTube links, try to extract date from the video title
            if not meeting_date and LinkScraper._is_youtube_link(media_url):
                if media_url not in youtube_titles:
                    youtube_title = LinkScraper._get_youtube_title(media_url)
                    youtube_titles[media_url] = youtube_title
                
                youtube_title = youtube_titles[media_url]
                if youtube_title:
                    youtube_title_date = LinkScraper._parse_date(youtube_title)
                    if youtube_title_date:
                        meeting_date = youtube_title_date
                        print(f"DEBUG: Extracted date from YouTube title: {youtube_title} -> {youtube_title_date}")
            
            # Determine document type
            document_type = LinkScraper._determine_document_type(link_text)
            
            # Check if it's a video file and update document type accordingly
            if any(media_url.lower().endswith(ext) for ext in video_extensions) or LinkScraper._is_youtube_link(media_url) or media_url in google_drive_video_filenames:
                document_type = "video"
            
            # If date extraction successful and date is within range
            if meeting_date and LinkScraper._is_date_in_range(meeting_date, start_date, end_date):
                meeting["date"] = meeting_date
                meeting[document_type] = media_url
                
                # Add additional info if available
                if link_text:
                    meeting["title"] = link_text
                
                meetings.append(meeting)
                print(f"DEBUG: Added meeting: {meeting}")
        
        # print(f"DEBUG: Total meetings found: {len(meetings)}")
        
        # Merge meetings that belong to the same meeting using LCS
        merged_meetings = LinkScraper._merge_meetings_by_date_and_matching(meetings)
        
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
            html_content = asyncio.run(LinkScraper._load_page_with_playwright(url))
            
            if html_content is None:
                return None
            
            # Extract PDF data with date filtering
            meetings = LinkScraper._extract_pdf_data(html_content, url, start_date, end_date)
            
            if meetings is None:
                return None
            
            return meetings
            
        except Exception as e:
            print(f"Error in LinkScraper for {url}: {e}")
            return None