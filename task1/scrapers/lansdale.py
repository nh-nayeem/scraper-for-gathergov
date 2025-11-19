from typing import List, Dict, Any
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import os
from pathlib import Path
import re
from playwright.sync_api import sync_playwright

class LansdaleScraper:
    
    @staticmethod
    def get_meeting(page, video_url: str) -> Dict[str, Any]:
        """
        Extract meeting data from a single Lansdale video page.
        
        Args:
            page: Playwright page object
            video_url: URL of the individual video page
            
        Returns:
            Dictionary containing meeting data or None if extraction fails
        """
        try:
            # Navigate to the video page
            page.goto(video_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_load_state('networkidle', timeout=15000)
            
            # Get video page content
            video_content = page.content()
            video_soup = BeautifulSoup(video_content, 'html.parser')
            
            # Extract title from h2 with id="videoName"
            title_elem = video_soup.find('h2', id="videoName")
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            
            # Extract date from videoMeta div
            date_str = ""
            video_meta = video_soup.find('div', class_='videoMeta')
            if video_meta:
                # Look for "Uploaded:" pattern
                uploaded_dd = video_meta.find('dd', class_='first')
                if uploaded_dd:
                    date_str = uploaded_dd.get_text(strip=True)
            
            if not date_str:
                return None
            
            # Parse date from format like "December 19, 2024"
            try:
                date_obj = datetime.strptime(date_str, "%B %d, %Y")
                formatted_date = date_obj.strftime("%Y-%m-%d")
            except ValueError:
                return None
            
            return {
                "meeting_url": video_url,
                "agenda_url": "",  # Lansdale doesn't have agenda URLs
                "minutes_url": "",  # Lansdale doesn't have minutes URLs
                "title": title,
                "date": formatted_date
            }
            
        except Exception as e:
            return None

    @staticmethod
    def scrape_url(base_url: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Scrape meeting video data from Lansdale CivicMedia page.
        
        Args:
            base_url: Base URL of the Lansdale CivicMedia page
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List of dictionaries containing meeting data
        """
        meetings_data = []
        
        # Create debug directory and log file
        debug_dir = Path("debug")
        debug_dir.mkdir(exist_ok=True)
        debug_log = debug_dir / "lansdale_meetings.log"
        
        # Initialize debug log
        with open(debug_log, 'w', encoding='utf-8') as f:
            f.write(f"Lansdale Meeting Scraper Debug Log\n")
            f.write(f"===================================\n")
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
                
                # Visit the base URL
                page.goto(base_url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_load_state('networkidle', timeout=30000)
                
                # Get initial page to extract video links
                content = page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                # base url also contain meeting data
                base_url_data = LansdaleScraper.get_meeting(page, base_url)
                if base_url_data is not None and start_date <= base_url_data["date"] <= end_date:
                    meetings_data.append(base_url_data)

                # Find all video links in the listing
                video_links = soup.find_all('a', href=lambda x: x and 'CivicMedia.aspx' in x and 'VID=' in x)
                
                # for link in video_links:
                #     video_href = link['href']
                #     video_url = urljoin(base_url, video_href)
                #     print(f"Raw href: {video_href} -> Full URL: {video_url}")

                log_debug(f"[*] Found {len(video_links)} video links on the page")
                
                if not video_links:
                    print("No video links found")
                    log_debug("[!] No video links found")
                    return meetings_data
                
                total_processed = 0
                total_in_range = 0
                
                for idx, link in enumerate(video_links, 1):
                    try:
                        log_debug(f"\n--- Processing Video #{idx} ---")
                        
                        # Get the video URL
                        video_href = link['href']
                        video_url = urljoin(base_url, video_href)
                        log_debug(f"    Video URL: {video_url}")
                        
                        # Use get_meeting function to extract data
                        log_debug(f"    [*] Extracting meeting data...")
                        meeting_data = LansdaleScraper.get_meeting(page, video_url)
                        
                        if meeting_data is None:
                            log_debug("    [!] Failed to extract meeting data")
                            continue
                        
                        total_processed += 1
                        
                        # Check if date is within range
                        if start_date <= meeting_data["date"] <= end_date:
                            total_in_range += 1
                            meetings_data.append(meeting_data)
                            log_debug(f"    [+] INCLUDED - Meeting within date range")
                            log_debug(f"        Title: {meeting_data['title']}")
                        else:
                            log_debug(f"    [-] SKIPPED - Meeting outside date range ({start_date} to {end_date})")
                            log_debug(f"        Title: {meeting_data['title']}")
                        
                    except Exception as e:
                        print(f"Error processing video: {e}")
                        log_debug(f"    [!] Error processing video: {e}")
                        continue
                
                log_debug(f"\n=== Summary ===")
                log_debug(f"Total videos processed: {total_processed}")
                log_debug(f"Videos within date range: {total_in_range}")
                log_debug(f"Meetings added to results: {len(meetings_data)}")
                
                # # Print summary to console
                # print(f"Lansdale scraping complete. Found {len(meetings_data)} meetings within date range.")
                # print(f"Total videos processed: {total_processed} | See debug/lansdale_meetings.log for details")
                
            except Exception as e:
                print(f"Error processing {base_url}: {e}")
                log_debug(f"[!] Critical error: {e}")
            
            finally:
                page.close()
                context.close()
                browser.close()
        
        return meetings_data