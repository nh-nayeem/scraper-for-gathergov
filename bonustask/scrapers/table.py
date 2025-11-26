import re
from datetime import datetime
from token import EQUAL
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional
from . import utils

class TableScraper:
    @staticmethod
    def _normalize_url(url: str, base_url: str) -> str:
        """Normalize URL - convert relative URLs to absolute."""
        return utils.normalize_url(url, base_url)
    
    @staticmethod
    def _parse_date(date_str: str) -> Optional[str]:
        """Parse date string in various formats and return YYYY-MM-DD format."""
        return utils.parse_date(date_str)
    
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
        
        if "youtube.com/watch?v=" in text_lower:
            return "youtube"
        # If no keyword matches, return original text
        return cell_text
    
    @staticmethod
    def _add_unique_key(meeting: Dict[str, Any], key_counts: Dict[str, int], key: str, value: str) -> None:
        """Add a key-value pair to meeting dict, adding suffix if key already exists."""
        if key not in meeting:
            meeting[key] = value
            key_counts[key] = 1
        elif key != "date" and meeting[key] != value:
            # Key exists, always add suffix for duplicate keys
            key_counts[key] = key_counts.get(key, 1) + 1
            # Create new key with suffix
            new_key = f"{key};{key_counts[key]:02d}"
            meeting[new_key] = value
    
    @staticmethod
    def _extract_table_data(html_content: str, base_url: str, start_date: str, end_date: str, debug_log=None) -> List[Dict[str, Any]]:
        """Extract meeting data from table rows using BeautifulSoup."""
        soup = BeautifulSoup(html_content, 'html.parser')
        meetings = []
        
        def debug_log_write(message):
            """Write debug message to log file if available."""
            if debug_log:
                with open(debug_log, 'a', encoding='utf-8') as f:
                    f.write(f"{datetime.now().isoformat()} - TABLE_SCRAPER: {message}\n")
        
        def process_table_body(table_body, depth=0):
            """Recursively process table body and nested table bodies."""
            if depth > 10:  # Prevent infinite recursion
                debug_log_write(f"Maximum recursion depth reached at depth {depth}")
                return []
            
            local_meetings = []
            debug_log_write(f"Processing table body at depth {depth}")
            
            # Find all <tr> elements in this table body
            tr_elements = table_body.find_all('tr')
            debug_log_write(f"Found {len(tr_elements)} <tr> elements at depth {depth}")
            
            for tr_idx, tr in enumerate(tr_elements):
                # Check if this <tr> contains another table body
                nested_table_body = tr.find('tbody')
                if nested_table_body:
                    debug_log_write(f"<tr> {tr_idx} contains nested table body, recursing into it")
                    # Recursively process the nested table body
                    nested_meetings = process_table_body(nested_table_body, depth + 1)
                    local_meetings.extend(nested_meetings)
                    continue
                
                # Filter out pagination/navigation rows before processing
                cells = tr.find_all(['td', 'th'])
                if cells:
                    cell_texts = [cell.get_text(strip=True) for cell in cells]
                    
                    # Skip rows with only navigation symbols or single digits
                    nav_symbols = ['<<', '>>', '<', '>', '...', 'select']
                    has_only_nav = all(text in nav_symbols or (text.isdigit() and len(text) <= 2) for text in cell_texts if text)
                    
                    # Skip rows that are purely pagination/calendar
                    if has_only_nav:
                        debug_log_write(f"Skipping pagination row {tr_idx} at depth {depth}: {cell_texts}")
                        continue
                    
                    # Check if this row has meeting-related content
                    has_date = any(TableScraper._parse_date(text) for text in cell_texts)
                    has_meeting_keywords = any(keyword in ' '.join(cell_texts).lower() for keyword in ['regular', 'session', 'meeting', 'council', 'workshop'])
                    has_pdf_links = any(cell.find('a', href=re.compile(r'DisplayAgendaPDF\.ashx\?MeetingID=|\.pdf$', re.IGNORECASE)) for cell in cells)
                    
                    # Only process rows that look like actual meetings
                    if not (has_date or has_meeting_keywords or has_pdf_links):
                        debug_log_write(f"Skipping non-meeting row {tr_idx} at depth {depth}: {cell_texts}")
                        continue
                
                # Process this <tr> as a potential meeting row
                meeting = {}
                meeting_date = None
                key_counts = {}  # Track key occurrences for suffix handling
                
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
                    
                    # Clean up cell text: remove newlines and extra whitespace
                    cell_text = re.sub(r'\s+', ' ', cell_text).strip()
                    
                    # Check if this cell contains date information
                    parsed_date = TableScraper._parse_date(cell_text)
                    if parsed_date:
                        meeting_date = parsed_date
                        # Use "date" as key and the actual parsed date as value
                        key = "date"
                        value = parsed_date
                        TableScraper._add_unique_key(meeting, key_counts, key, value)
                        
                        # Also store the original cell text as a key with the link as value
                        # This handles cases where "August 14, 2025" is both a date and a key
                        links = cell.find_all('a')
                        if links:
                            for i, link in enumerate(links):
                                href = link.get('href')
                                if href:
                                    normalized_url = TableScraper._normalize_url(href, base_url)
                                    # For multiple links, add index suffix after the key
                                    link_text = link.get_text(strip=True)
                                    link_key = TableScraper._normalize_key(link_text)
                                    TableScraper._add_unique_key(meeting, key_counts, link_key, normalized_url)
                    else:
                        # Use normalized key for non-date data
                        key = TableScraper._normalize_key(cell_text)
                        
                        # Extract all links from this cell, including those in nested tables
                        all_links = cell.find_all('a')
                        
                        if all_links:
                            # Process all links found in this cell (including nested table links)
                            for i, link in enumerate(all_links):
                                href = link.get('href')
                                if href:
                                    # Normalize the URL
                                    normalized_url = TableScraper._normalize_url(href, base_url)
                                    # For multiple links, add index suffix after the key
                                    link_text = link.get_text(strip=True)
                                    link_key = TableScraper._normalize_key(link_text)
                                    TableScraper._add_unique_key(meeting, key_counts, link_key, normalized_url)
                        else:
                            # If no link, use cell text as value
                            if cell_text != key and len(cell_text) > 2:
                                TableScraper._add_unique_key(meeting, key_counts, key, cell_text)
                
                # Only add meeting if we have some data
                if meeting:
                    debug_log_write(f"Row {tr_idx} at depth {depth} produced meeting data: {list(meeting.keys())}")
                    
                    # If no date was found in primary fields, try to extract from other values
                    if "date" not in meeting:
                        for key, value in meeting.items():
                            # Check both key and value for dates
                            for text_to_check in [key, value]:
                                if isinstance(text_to_check, str):
                                    extracted_date = TableScraper._parse_date(text_to_check)
                                    if extracted_date:
                                        meeting_date = extracted_date
                                        meeting["date"] = extracted_date
                                        break
                            if "date" in meeting:
                                break
                    
                    # Check if meeting is in date range
                    if "date" in meeting and TableScraper._is_date_in_range(meeting_date, start_date, end_date):
                        # Check if meeting has at least one media data
                        if TableScraper._has_media_data(meeting):
                            local_meetings.append(meeting)
                            debug_log_write(f"Added meeting with date {meeting_date} at depth {depth}")
                        else:
                            debug_log_write(f"Meeting rejected - no media data at depth {depth}")
                    else:
                        debug_log_write(f"Meeting rejected - date {meeting_date} not in range at depth {depth}")
                else:
                    debug_log_write(f"Row {tr_idx} at depth {depth} produced no meeting data")
            
            return local_meetings
        
        # Find all tables and debug the structure
        all_tables = soup.find_all('table')
        debug_log_write(f"Found {len(all_tables)} total tables")
        
        # Process each table
        for table_idx, table in enumerate(all_tables):
            debug_log_write(f"Processing table {table_idx}")
            
            # Find table body
            table_body = table.find('tbody')
            if not table_body:
                # If no tbody, use the table itself
                table_body = table
                debug_log_write(f"No tbody found in table {table_idx}, using table element")
            else:
                debug_log_write(f"Found tbody in table {table_idx}")
            
            # Process the table body recursively
            table_meetings = process_table_body(table_body, 0)
            meetings.extend(table_meetings)
        
        debug_log_write(f"Final result: {len(meetings)} meetings found")
        return meetings if meetings else None
    
    @staticmethod
    def try_scrape(html_content: str, url: str, start_date: str, end_date: str, debug_log=None) -> Optional[List[Dict[str, Any]]]:
        """Try to scrape meeting data using table-based approach.
        
        Args:
            html_content: The HTML content to parse
            url: The URL that was scraped
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Meeting data if successful, None if unsuccessful
        """
        try:
            if html_content is None:
                return None
            
            # Extract table data with date filtering and media validation
            meetings = TableScraper._extract_table_data(html_content, url, start_date, end_date, debug_log)
            
            if meetings is None:
                return None
            
            return meetings
            
        except Exception as e:
            print(f"Error in TableScraper for {url}: {e}")
            return None