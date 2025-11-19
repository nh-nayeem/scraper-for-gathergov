from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import Dict, Any, List
from datetime import datetime
import requests
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

class BethlehemScraper:
    def scrape_url(base_url: str, start_date: str, end_date: str) -> List[Dict[str, str]]:
        """
        Scrape meeting data from Bethlehem website by iterating through meeting URLs.
        
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
        debug_log = debug_dir / "bethlehem_meetings.log"
        
        # Initialize debug log
        with open(debug_log, 'w', encoding='utf-8') as f:
            f.write(f"Bethlehem Meeting Scraper Debug Log\n")
            f.write(f"===================================\n")
            f.write(f"Base URL: {base_url}\n")
            f.write(f"Date Range: {start_date} to {end_date}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n\n")
        
        def log_debug(message: str):
            """Write debug message to log file"""
            with open(debug_log, 'a', encoding='utf-8') as f:
                f.write(f"{message}\n")
        
        # Playwright browser management
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            try:
                total_checked = 0
                total_valid = 0
                total_in_range = 0
                
                # Iterate through City Council Meetings
                log_debug("[*] Starting City Council Meetings scan...")
                print("Scanning City Council Meetings...")
                
                for i in range(1, 601):
                    meeting_url = f"{base_url}/Meetings/2025/City-Council-Meetings/{i}"
                    total_checked += 1
                    
                    # First check if URL is valid with a simple request
                    try:
                        response = requests.get(meeting_url, timeout=10)
                        if response.status_code != 200:
                            log_debug(f"    [-] Invalid URL: {meeting_url} (Status: {response.status_code})")
                            continue
                    except requests.RequestException as e:
                        log_debug(f"    [-] Request failed for {meeting_url}: {e}")
                        continue
                    
                    total_valid += 1
                    log_debug(f"    [+] Valid URL found: {meeting_url}")
                    
                    # Now scrape the meeting data using Playwright
                    try:
                        page.goto(meeting_url, wait_until="domcontentloaded")
                        page.wait_for_load_state('networkidle', timeout=30000)
                        
                        content = page.content()
                        soup = BeautifulSoup(content, 'html.parser')
                        
                        # Extract meeting info from dl.single-calendar-info
                        info_dl = soup.select_one('dl.single-calendar-info')
                        if not info_dl:
                            log_debug(f"        [!] No meeting info found for {meeting_url}")
                            continue
                        
                        # Extract title
                        title_dt = info_dl.find('dt', string=lambda text: text and 'Meeting Title:' in text)
                        title_dd = title_dt.find_next_sibling('dd') if title_dt else None
                        title = title_dd.get_text(strip=True) if title_dd else "No title"
                        
                        # Extract date
                        date_dt = info_dl.find('dt', string=lambda text: text and 'Date:' in text)
                        date_dd = date_dt.find_next_sibling('dd') if date_dt else None
                        date_str = date_dd.get_text(strip=True) if date_dd else ""
                        
                        # Extract time
                        time_dt = info_dl.find('dt', string=lambda text: text and 'Time:' in text)
                        time_dd = time_dt.find_next_sibling('dd') if time_dt else None
                        time_str = time_dd.get_text(strip=True) if time_dd else ""
                        
                        # Parse date to YYYY-MM-DD format
                        try:
                            # Extract date from string like "Tuesday, September 16, 2025"
                            date_parts = date_str.split(',')
                            if len(date_parts) >= 3:
                                date_without_day = ','.join(date_parts[1:]).strip()
                                date_obj = datetime.strptime(date_without_day, "%B %d, %Y")
                                formatted_date = date_obj.strftime("%Y-%m-%d")
                            else:
                                continue
                        except (ValueError, IndexError) as e:
                            log_debug(f"        [!] Date parsing failed: {e}")
                            continue
                        
                        # Check if meeting is within date range
                        if formatted_date < start_date or formatted_date > end_date:
                            log_debug(f"        [-] Meeting outside date range: {formatted_date}")
                            continue
                        
                        # Extract meeting links from div with p.btn-container
                        agenda_url = minutes_url = audio_url = video_url = ""
                        
                        link_containers = soup.select('p.btn-container a.blue-btn')
                        for link in link_containers:
                            href = link.get('href', '')
                            link_text = link.get_text(strip=True).lower()
                            
                            if 'agenda' in link_text:
                                agenda_url = urljoin(base_url, href)
                            elif 'meeting minutes: text' in link_text:
                                minutes_url = urljoin(base_url, href)
                            elif 'meeting minutes: audio' in link_text:
                                audio_url = urljoin(base_url, href)
                            elif 'meeting minutes: video' in link_text:
                                video_url = href if href.startswith('http') else urljoin(base_url, href)
                        
                        total_in_range += 1
                        
                        meeting_data = {
                            "meeting_url": video_url,
                            "agenda_url": agenda_url,
                            "minutes_url": minutes_url,
                            "audio_url": audio_url,
                            "title": title,
                            "date": formatted_date,
                            "time": time_str
                        }
                        
                        meetings_data.append(meeting_data)
                        log_debug(f"        [+] Meeting added: {title} on {formatted_date}")
                        
                    except Exception as e:
                        log_debug(f"        [!] Error scraping {meeting_url}: {e}")
                        continue
                
                # Iterate through Committee Meetings
                log_debug("[*] Starting Committee Meetings scan...")
                print("Scanning Committee Meetings...")
                
                for i in range(1, 601):
                    meeting_url = f"{base_url}/Meetings/2025/Committee-Meetings/{i}"
                    total_checked += 1
                    
                    # First check if URL is valid with a simple request
                    try:
                        response = requests.get(meeting_url, timeout=10)
                        if response.status_code != 200:
                            log_debug(f"    [-] Invalid URL: {meeting_url} (Status: {response.status_code})")
                            continue
                    except requests.RequestException as e:
                        log_debug(f"    [-] Request failed for {meeting_url}: {e}")
                        continue
                    
                    total_valid += 1
                    log_debug(f"    [+] Valid URL found: {meeting_url}")
                    
                    # Now scrape the meeting data using Playwright
                    try:
                        page.goto(meeting_url, wait_until="domcontentloaded")
                        page.wait_for_load_state('networkidle', timeout=30000)
                        
                        content = page.content()
                        soup = BeautifulSoup(content, 'html.parser')
                        
                        # Extract meeting info from dl.single-calendar-info
                        info_dl = soup.select_one('dl.single-calendar-info')
                        if not info_dl:
                            log_debug(f"        [!] No meeting info found for {meeting_url}")
                            continue
                        
                        # Extract title
                        title_dt = info_dl.find('dt', string=lambda text: text and 'Meeting Title:' in text)
                        title_dd = title_dt.find_next_sibling('dd') if title_dt else None
                        title = title_dd.get_text(strip=True) if title_dd else "No title"
                        
                        # Extract date
                        date_dt = info_dl.find('dt', string=lambda text: text and 'Date:' in text)
                        date_dd = date_dt.find_next_sibling('dd') if date_dt else None
                        date_str = date_dd.get_text(strip=True) if date_dd else ""
                        
                        # Extract time
                        time_dt = info_dl.find('dt', string=lambda text: text and 'Time:' in text)
                        time_dd = time_dt.find_next_sibling('dd') if time_dt else None
                        time_str = time_dd.get_text(strip=True) if time_dd else ""
                        
                        # Parse date to YYYY-MM-DD format
                        try:
                            # Extract date from string like "Tuesday, September 16, 2025"
                            date_parts = date_str.split(',')
                            if len(date_parts) >= 3:
                                date_without_day = ','.join(date_parts[1:]).strip()
                                date_obj = datetime.strptime(date_without_day, "%B %d, %Y")
                                formatted_date = date_obj.strftime("%Y-%m-%d")
                            else:
                                continue
                        except (ValueError, IndexError) as e:
                            log_debug(f"        [!] Date parsing failed: {e}")
                            continue
                        
                        # Check if meeting is within date range
                        if formatted_date < start_date or formatted_date > end_date:
                            log_debug(f"        [-] Meeting outside date range: {formatted_date}")
                            continue
                        
                        # Extract meeting links from div with p.btn-container
                        agenda_url = minutes_url = audio_url = video_url = ""
                        
                        link_containers = soup.select('p.btn-container a.blue-btn')
                        for link in link_containers:
                            href = link.get('href', '')
                            link_text = link.get_text(strip=True).lower()
                            
                            if 'agenda' in link_text:
                                agenda_url = urljoin(base_url, href)
                            elif 'meeting minutes: text' in link_text:
                                minutes_url = urljoin(base_url, href)
                            elif 'meeting minutes: audio' in link_text:
                                audio_url = urljoin(base_url, href)
                            elif 'meeting minutes: video' in link_text:
                                video_url = href if href.startswith('http') else urljoin(base_url, href)
                        
                        total_in_range += 1
                        
                        meeting_data = {
                            "meeting_url": video_url,
                            "agenda_url": agenda_url,
                            "minutes_url": minutes_url,
                            "audio_url": audio_url,
                            "title": title,
                            "date": formatted_date,
                            "time": time_str
                        }
                        
                        meetings_data.append(meeting_data)
                        log_debug(f"        [+] Meeting added: {title} on {formatted_date}")
                        
                    except Exception as e:
                        log_debug(f"        [!] Error scraping {meeting_url}: {e}")
                        continue
                
                # Log summary
                log_debug(f"\n=== Summary ===")
                log_debug(f"Total URLs checked: {total_checked}")
                log_debug(f"Valid URLs found: {total_valid}")
                log_debug(f"Meetings within date range: {total_in_range}")
                log_debug(f"Meetings added to results: {len(meetings_data)}")
                
                # Print summary to console
                print(f"Scraping complete. Found {len(meetings_data)} meetings within date range.")
                print(f"Total URLs checked: {total_checked} | Valid URLs: {total_valid}")
                print(f"See debug/bethlehem_meetings.log for details")
                
            except Exception as e:
                print(f"Error during scraping: {e}")
                log_debug(f"[!] Critical error: {e}")
            
            finally:
                page.close()
                context.close()
                browser.close()
        
        return meetings_data