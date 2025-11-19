from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import Dict, Any, List
from datetime import datetime
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

class CityOfVenturaScraper:
    def scrape_url(base_url: str, start_date: str, end_date: str) -> List[Dict[str, str]]:
        """
        Scrape meeting data from City of Ventura website.
        
        Args:
            base_url: Base URL of the website
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List of dictionaries containing meeting data
        """
        meetings_data = []
        
        # Create debug directory and log file
        debug_dir = Path("debug")
        debug_dir.mkdir(exist_ok=True)
        debug_log = debug_dir / "cityofventura_meetings.log"
        
        # Initialize debug log
        with open(debug_log, 'w', encoding='utf-8') as f:
            f.write(f"City of Ventura Meeting Scraper Debug Log\n")
            f.write(f"=========================================\n")
            f.write(f"Scraping URL: {base_url}\n")
            f.write(f"Date Range: {start_date} to {end_date}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n\n")
        
        def log_debug(message: str):
            """Write debug message to log file"""
            with open(debug_log, 'a', encoding='utf-8') as f:
                f.write(f"{message}\n")
        
        # Playwright browser management is now inside this scraper
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            try:
                print(f"Accessing {base_url}...")
                log_debug(f"[*] Accessing {base_url}...")
                page.goto(base_url, wait_until="domcontentloaded")
                page.wait_for_load_state('networkidle', timeout=30000)
                
                # Get the page content after JavaScript execution
                content = page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Find all meeting rows with minutes
                meetings = soup.select('tr.catAgendaRow')
                
                log_debug(f"[*] Found {len(meetings)} meeting rows with class 'catAgendaRow'")
                
                if not meetings:
                    print("No meeting rows found with class 'catAgendaRow'")
                    log_debug("[!] No meeting rows found with class 'catAgendaRow'")
                    return meetings_data
                
                total_processed = 0
                total_in_range = 0
                
                for idx, meeting in enumerate(meetings, 1):
                    try:
                        log_debug(f"\n--- Processing Meeting #{idx} ---")
                        
                        # Get minutes URL from td.minutes > a
                        minutes_url = ""
                        minutes_elem = meeting.select_one('td.minutes a')
                        if minutes_elem and minutes_elem.has_attr('href'):
                            minutes_url = urljoin(base_url, minutes_elem['href'])
                        
                        # Get meeting title and agenda URL from the row
                        title_elem = meeting.select_one('td:first-child p a')
                        title = title_elem.get_text(strip=True) if title_elem else "No title"
                        agenda_url = urljoin(base_url, title_elem['href']) if title_elem and title_elem.has_attr('href') else ""
                        
                        # Get YouTube video URL if available
                        video_elem = meeting.select_one('td.media a[href^="https://www.youtube.com/"]')
                        video_url = video_elem['href'] if video_elem else ""
            
                        # Extract and format the date
                        date_elem = meeting.select_one('td:first-child h3 strong')
                        date_str = date_elem.get_text(strip=True) if date_elem else ""
                        
                        try:
                            date_obj = datetime.strptime(date_str, "%b%d, %Y")
                            date_str = date_obj.strftime("%Y-%m-%d")
                        except ValueError as e:
                            log_debug(f"    [!] Date parsing failed: {e}")
                            continue  # Skip if date parsing fails
                        
                        total_processed += 1
                        
                        # Only include meetings within the date range
                        if date_str >= start_date and date_str <= end_date:
                            total_in_range += 1
                            meeting_data = {
                                "meeting_url": video_url,
                                "agenda_url": agenda_url,
                                "minutes_url": minutes_url,
                                "title": title,
                                "date": date_str
                            }
                            meetings_data.append(meeting_data)
                            # Move detailed meeting info to debug log only
                            log_debug(f"    [+] INCLUDED - Meeting within date range")
                            log_debug(f"        Title: {title}")
                        else:
                            log_debug(f"    [-] SKIPPED - Meeting outside date range ({start_date} to {end_date})")
                            log_debug(f"        Title: {title}")
                        
                    except Exception as e:
                        print(f"Error processing meeting: {e}")
                        log_debug(f"    [!] Error processing meeting: {e}")
                        continue
                
                log_debug(f"\n=== Summary ===")
                log_debug(f"Total meetings processed: {total_processed}")
                log_debug(f"Meetings within date range: {total_in_range}")
                log_debug(f"Meetings added to results: {len(meetings_data)}")
                
                # Print summary to console
                print(f"Scraping complete. Found {len(meetings_data)} meetings within date range.")
                print(f"Total meetings processed: {total_processed} | See debug/cityofventura_meetings.log for details")
                
            except Exception as e:
                print(f"Error processing {base_url}: {e}")
                log_debug(f"[!] Critical error: {e}")
            
            finally:
                page.close()
                context.close()
                browser.close()
        
        return meetings_data