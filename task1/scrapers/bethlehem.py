from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import Dict, Any, List
from datetime import datetime
import requests
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

class BethlehemScraper:
    @staticmethod
    def extract_hidden_fields(soup):
        """Extract hidden ASP.NET fields for postback"""
        data = {}
        for field in ["__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"]:
            tag = soup.find("input", {"name": field})
            if tag:
                data[field] = tag["value"]
        return data

    @staticmethod
    def get_next_argument(soup):
        """Extract EVENTARGUMENT for month navigation"""
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "__doPostBack" in href:
                try:
                    arg = href.split(",")[1]
                    arg = arg.replace(")", "").replace("'", "").strip()
                    return arg
                except:
                    continue
        return None

    @staticmethod
    def extract_meeting_urls(soup, base_url):
        """Extract meeting URLs from calendar popups"""
        events = []
        
        for div in soup.select("div.calendar-popup.modal"):
            # MORE link to meeting page
            more = div.select_one("p.marg-tp a[href]")
            if more:
                href = more["href"]
                if href.startswith("http"):
                    url = href
                else:
                    url = urljoin(base_url, href)
                events.append(url)
        
        return events

    @staticmethod
    def scrape_url(base_url: str, start_date: str, end_date: str) -> List[Dict[str, str]]:
        """
        Scrape meeting data from Bethlehem website by extracting meeting URLs from calendar.
        
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
        
        # First extract all meeting URLs from calendar
        session = requests.Session()
        all_meeting_urls = []
        seen_urls = set()  # Track URLs to avoid duplicates
        
        try:
            log_debug("[*] Starting calendar URL extraction...")
            print("Extracting meeting URLs from calendar...")
            
            # Load initial calendar page
            resp = session.get(base_url)
            soup = BeautifulSoup(resp.text, "lxml")
            today_date = datetime.now()
            target_date = datetime.strptime(start_date, "%Y-%m-%d")
            month_diff = (today_date - target_date).days // 30 + 1
            print("Previous Month to check:", month_diff)
            # Extract URLs from multiple months
            for month_num in range(month_diff):  
                log_debug(f"[*] Processing month {month_num + 1}...")
                
                # Extract meeting URLs for current month
                month_urls = BethlehemScraper.extract_meeting_urls(soup, base_url)
                # Deduplicate URLs
                unique_urls = []
                for url in month_urls:
                    if url not in seen_urls:
                        seen_urls.add(url)
                        unique_urls.append(url)
                all_meeting_urls.extend(unique_urls)
                log_debug(f"    [+] Found {len(month_urls)} meeting URLs this month ({len(unique_urls)} unique)")
                
                # Prepare for next month
                hidden = BethlehemScraper.extract_hidden_fields(soup)
                event_arg = BethlehemScraper.get_next_argument(soup)
                
                if not event_arg:
                    log_debug("[!] No next-month argument found. Stopping URL extraction.")
                    break
                
                log_debug(f"    [*] Switching to next month via EVENTARGUMENT = {event_arg}")
                
                # POSTBACK to load next month
                post_data = hidden.copy()
                post_data["__EVENTTARGET"] = "p$lt$ctl07$pageplaceholder$p$lt$ctl04$Calendar$calItems"
                post_data["__EVENTARGUMENT"] = event_arg
                
                resp = session.post(base_url, data=post_data)
                soup = BeautifulSoup(resp.text, "lxml")
            
            log_debug(f"[*] Total meeting URLs extracted: {len(all_meeting_urls)}")
            print(f"Found {len(all_meeting_urls)} total meeting URLs from calendar")
            
        except Exception as e:
            log_debug(f"[!] Error extracting meeting URLs: {e}")
            print(f"Error extracting meeting URLs: {e}")
            return meetings_data
        
        # Now scrape each meeting URL
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            try:
                total_processed = 0
                total_in_range = 0
                
                log_debug("[*] Starting individual meeting scraping...")
                print("Scraping individual meeting pages...")
                
                for idx, meeting_url in enumerate(all_meeting_urls, 1):
                    total_processed += 1
                    log_debug(f"[*] Processing meeting {idx}/{len(all_meeting_urls)}: {meeting_url}")
                    
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
                            "date": formatted_date
                        }
                        
                        meetings_data.append(meeting_data)
                        log_debug(f"        [+] Meeting added: {title} on {formatted_date}")
                        
                    except Exception as e:
                        log_debug(f"        [!] Error scraping {meeting_url}: {e}")
                        continue
                
                # Log summary
                log_debug(f"\n=== Summary ===")
                log_debug(f"Total meeting URLs found: {len(all_meeting_urls)}")
                log_debug(f"Total meetings processed: {total_processed}")
                log_debug(f"Meetings within date range: {total_in_range}")
                log_debug(f"Meetings added to results: {len(meetings_data)}")
                
                # Print summary to console
                print(f"Scraping complete. Found {len(meetings_data)} meetings within date range.")
                print(f"Total URLs processed: {total_processed}/{len(all_meeting_urls)}")
                print(f"See debug/bethlehem_meetings.log for details")
                
            except Exception as e:
                print(f"Error during meeting scraping: {e}")
                log_debug(f"[!] Critical error during meeting scraping: {e}")
            
            finally:
                page.close()
                context.close()
                browser.close()
        
        return meetings_data