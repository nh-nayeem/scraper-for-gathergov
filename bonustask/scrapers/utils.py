import re
from datetime import datetime
from urllib.parse import urljoin, urlparse
from typing import Optional


def parse_date(date_str: str) -> Optional[str]:
    """Parse date string in various formats and return YYYY-MM-DD format."""
    if not date_str:
        return None
    
    # Preprocess: remove ordinal suffixes (st, nd, rd, th)
    cleaned_date = re.sub(r'(\d+)(st|nd|rd|th)\b', r'\1', date_str)
    
    # Common date patterns to match
    patterns = [
        # Month DD, YYYY (full month names)
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s*(\d{1,2}),?\s+(\d{4})',
        # Abbreviated month names with or without periods (Jan., Jan, Aug., Aug, Sept., Sep)
        r'(Jan\.?|Feb\.?|Mar\.?|Apr\.?|May|Jun\.?|Jul\.?|Aug\.?|Sep\.?|Sept\.?|Oct\.?|Nov\.?|Dec\.?)\s*(\d{1,2}),?\s+(\d{4})',
        # DD Month YYYY
        r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})',
        # YYYY-MM-DD, YYYY/MM/DD
        r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',
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
                    elif pattern.startswith(r'(Jan\.?|Feb\.?|Mar\.?|Apr\.?|May|Jun\.?|Jul\.?|Aug\.?|Sep\.?|Sept\.?|Oct\.?|Nov\.?|Dec\.?)'):  # Abbreviated month names
                        month_str, day, year = groups
                        # Remove period if present and parse abbreviated month
                        month_str_clean = month_str.rstrip('.')
                        month = datetime.strptime(month_str_clean[:3], '%b').month
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


def normalize_url(url: str, base_url: str) -> str:
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