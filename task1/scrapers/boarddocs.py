from bs4 import BeautifulSoup
from typing import Dict, Any, List
from datetime import datetime
import json
from playwright.sync_api import sync_playwright
from pathlib import Path

class BoardDocsScraper:
    @staticmethod
    def scrape_url(base_url: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Scrape meeting data from BoardDocs website by extracting JSON from script tag.
        
        Args:
            base_url: Base URL of the BoardDocs website
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List of dictionaries containing meeting data
        """
        meetings_data = []
        
        # Create debug directory and log file
        debug_dir = Path("debug")
        debug_dir.mkdir(exist_ok=True)
        debug_log = debug_dir / "boarddocs_meetings.log"
        
        # Initialize debug log
        with open(debug_log, 'w', encoding='utf-8') as f:
            f.write(f"BoardDocs Meeting Scraper Debug Log\n")
            f.write(f"===================================\n")
            f.write(f"Base URL: {base_url}\n")
            f.write(f"Date Range: {start_date} to {end_date}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n\n")
        
        def log_debug(message: str):
            """Write debug message to log file"""
            with open(debug_log, 'a', encoding='utf-8') as f:
                f.write(f"{message}\n")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            try:
                print(f"Loading BoardDocs page: {base_url}")
                page.goto(base_url, wait_until="domcontentloaded")
                page.wait_for_load_state('networkidle', timeout=30000)
                
                content = page.content()
                
                soup = BeautifulSoup(content, 'html.parser')
                
                # Find all script tags in head for debugging
                all_scripts = soup.select('head script')
                log_debug(f"Found {len(all_scripts)} script tags in head")
                
                # Try to find the specific script tag with the JSON data
                script_tag = soup.select_one('head > script:nth-child(73)')
                if not script_tag:
                    log_debug("Could not find the script tag at position 73, checking other scripts...")
                    # Look for scripts that might contain JSON data
                    for i, script in enumerate(all_scripts):
                        if script.string and ('[' in script.string and ']' in script.string):
                            log_debug(f"Found potential JSON in script tag {i+1}")
                            script_tag = script
                            break
                
                if not script_tag:
                    log_debug("Could not find any script tag with JSON data")
                    return meetings_data
                
                script_content = script_tag.string
                if not script_content:
                    log_debug("Script tag is empty")
                    return meetings_data
                
                # Extract JSON from the script content
                # Look for JSON structure within the script
                try:
                    # Find JSON data - typically it starts with a variable assignment
                    # We'll look for JSON patterns in the script
                    json_start = script_content.find('[')
                    json_end = script_content.rfind(']') + 1
                    
                    if json_start == -1 or json_end == 0:
                        log_debug("Could not find JSON array in script content")
                        return meetings_data
                    
                    json_str = script_content[json_start:json_end]
                    meetings_json = json.loads(json_str)
                    
                    log_debug(f"Found {len(meetings_json)} meetings in JSON data")
                    
                    # Process each meeting
                    for meeting in meetings_json:
                        try:
                            # Extract required fields
                            name = meeting.get('name', '').strip()
                            start_date_str = meeting.get('startDate', '')
                            meeting_url = meeting.get('url', '').strip()
                            
                            if not name or not start_date_str or not meeting_url:
                                continue
                            
                            # Parse the date - BoardDocs dates are typically in ISO format
                            try:
                                # Handle various date formats
                                if 'T' in start_date_str:
                                    # ISO format with time
                                    date_obj = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
                                else:
                                    # Date only format
                                    date_obj = datetime.strptime(start_date_str, '%Y-%m-%d')
                                
                                formatted_date = date_obj.strftime('%Y-%m-%d')
                            except ValueError as e:
                                log_debug(f"Date parsing failed for {start_date_str}: {e}")
                                continue
                            
                            # Check if meeting is within date range
                            if formatted_date <= start_date or formatted_date >= end_date:
                                continue
                            
                            meeting_data = {
                                "meeting_url": meeting_url,
                                "agenda_url": "can be downloaded from the meeting_url by a python script",
                                "minutes_url": "can be downloaded from the meeting_url by a python script",
                                "title": name,
                                "date": formatted_date
                            }
                            
                            meetings_data.append(meeting_data)
                            log_debug(f"Added meeting: {name} on {formatted_date}")
                            
                        except Exception as e:
                            log_debug(f"Error processing meeting: {e}")
                            continue
                    
                except json.JSONDecodeError as e:
                            log_debug(f"Failed to parse JSON data: {e}")
                            return meetings_data
                
                log_debug(f"Successfully extracted {len(meetings_data)} meetings within date range")
                print(f"Successfully extracted {len(meetings_data)} meetings within date range")
                
            except Exception as e:
                log_debug(f"Error during BoardDocs scraping: {e}")
                print(f"Error during BoardDocs scraping: {e}")
            
            finally:
                page.close()
                context.close()
                browser.close()
        
        return meetings_data