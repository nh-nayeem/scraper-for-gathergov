from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import Dict, Any, List
from datetime import datetime
import os
from pathlib import Path
import re
from playwright.sync_api import sync_playwright

class FacebookScraper:
    
    def scrape_url(base_url: str, start_date: str, end_date: str) -> List[Dict[str, str]]:
        """
        Scrape meeting video data from Facebook page.
        
        Args:
            base_url: Base URL of the Facebook page
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List of dictionaries containing meeting data
        """
        meetings_data = []
        
        # Create debug directory and log file
        debug_dir = Path("debug")
        debug_dir.mkdir(exist_ok=True)
        debug_log = debug_dir / "facebook_meetings.log"
        
        # Initialize debug log
        with open(debug_log, 'w', encoding='utf-8') as f:
            f.write(f"Facebook Meeting Scraper Debug Log\n")
            f.write(f"==================================\n")
            f.write(f"Scraping URL: {base_url}\n")
            f.write(f"Date Range: {start_date} to {end_date}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n\n")
        
        def log_debug(message: str):
            """Write debug message to log file"""
            with open(debug_log, 'a', encoding='utf-8') as f:
                f.write(f"{message}\n")
        
        try:
            print(f"Accessing {base_url}...")
            log_debug(f"[*] Accessing {base_url}...")
            
            # Playwright browser management is now inside this scraper
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)  # Facebook might need non-headless for popups
                context = browser.new_context()
                page = context.new_page()
                
                try:
                    # Navigate to Facebook page with more flexible loading
                    try:
                        page.goto(base_url, wait_until="domcontentloaded", timeout=60000)
                    except Exception as e:
                        log_debug(f"[!] Initial navigation failed: {e}")
                        # Try with minimal wait
                        page.goto(base_url, timeout=30000)
                    
                    # Wait a bit for any dynamic content
                    page.wait_for_timeout(3000)
                    
                    # Try to close login popup if it appears
                    try:
                        # Look for close button in login popup
                        close_selectors = [
                            '[aria-label="Close"]',
                            '[data-testid="dialog-close-button"]',
                            'button[aria-label*="close"]',
                            '.x1i10hfl[aria-label="Close"]'
                        ]
                        
                        for selector in close_selectors:
                            try:
                                close_btn = page.locator(selector).first
                                if close_btn.is_visible():
                                    close_btn.click()
                                    log_debug(f"[*] Closed login popup with selector: {selector}")
                                    page.wait_for_timeout(1000)
                                    break
                            except:
                                continue
                    except Exception as e:
                        log_debug(f"[!] Could not close login popup: {e}")
                    
                    # Try to wait for networkidle but don't fail if it times out
                    try:
                        page.wait_for_load_state('networkidle', timeout=10000)
                    except:
                        log_debug("[!] Networkidle timeout, continuing anyway...")
                    
                    # Scroll down to load more videos
                    print("Scrolling to load more videos...")
                    for i in range(4):  # Scroll 3 times
                        try:
                            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            page.wait_for_timeout(2000)  # Wait 2 seconds between scrolls
                        except Exception as e:
                            log_debug(f"[!] Scroll attempt {i+1} failed: {e}")
                            break
                    
                    # Get the page content after JavaScript execution
                    content = page.content()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Extract video links directly - no need for containers
                    video_links = soup.find_all('a', href=lambda x: x and 'videos' in x)
                    
                    log_debug(f"[*] Found {len(video_links)} video links")
                    
                    if not video_links:
                        print("No video links found")
                        log_debug("[!] No video links found")
                        
                        # Save page content for debugging
                        with open(debug_dir / "facebook_page_content.html", 'w', encoding='utf-8') as f:
                            f.write(content)
                        log_debug("[*] Page content saved to facebook_page_content.html for inspection")
                        
                        return meetings_data
                    
                    total_processed = 0
                    total_in_range = 0
                    
                    for idx, link in enumerate(video_links, 1):
                        try:
                            log_debug(f"\n--- Processing Video #{idx} ---")
                            
                            # Get video URL from the link
                            video_url = link['href']
                            log_debug(f"    Video URL: {video_url}")
                            
                            # Get title from the link or its parent elements
                            title = ""
                            
                            # Try to get title from the link text
                            link_text = link.get_text(strip=True)
                            if link_text:
                                title = link_text
                            else:
                                # Try to find title in nearby spans
                                parent = link.find_parent()
                                if parent:
                                    title_span = parent.find('span', class_=lambda x: x and 'x1lliihq' in x and 'x6ikm8r' in x and 'x10wlt62' in x and 'x1n2onr6' in x)
                                    if title_span:
                                        title = title_span.get_text(strip=True)
                            
                            if not title:
                                log_debug("    [!] No title found")
                                continue
                            
                            log_debug(f"    Title: {title}")
                            
                            # Extract date from title using regex
                            # Pattern matches M/D/YYYY or MM/DD/YYYY format
                            date_pattern = r'(\d{1,2})/(\d{1,2})/(\d{4})'
                            date_match = re.search(date_pattern, title)
                            
                            if not date_match:
                                log_debug("    [!] No date found in title")
                                continue
                            
                            month, day, year = date_match.groups()
                            try:
                                # Convert to YYYY-MM-DD format for comparison
                                date_obj = datetime.strptime(f"{month}/{day}/{year}", "%m/%d/%Y")
                                formatted_date = date_obj.strftime("%Y-%m-%d")
                                log_debug(f"    Formatted Date: {formatted_date}")
                            except ValueError as e:
                                log_debug(f"    [!] Date parsing failed: {e}")
                                continue
                            
                            total_processed += 1
                            
                            # Check if date is within range
                            if start_date <= formatted_date <= end_date:
                                total_in_range += 1
                                meeting_data = {
                                    "meeting_url": video_url,
                                    "agenda_url": "",  # Facebook doesn't have agenda URLs
                                    "minutes_url": "",  # Facebook doesn't have minutes URLs
                                    "title": title,
                                    "date": formatted_date
                                }
                                meetings_data.append(meeting_data)
                                log_debug(f"    [+] INCLUDED - Meeting within date range")
                            else:
                                log_debug(f"    [-] SKIPPED - Meeting outside date range ({start_date} to {end_date})")
                            
                        except Exception as e:
                            print(f"Error processing video: {e}")
                            log_debug(f"    [!] Error processing video: {e}")
                            continue
                    
                    log_debug(f"\n=== Summary ===")
                    log_debug(f"Total videos processed: {total_processed}")
                    log_debug(f"Videos within date range: {total_in_range}")
                    log_debug(f"Meetings added to results: {len(meetings_data)}")
                    
                    # Print summary to console
                    print(f"Facebook scraping complete. Found {len(meetings_data)} meetings within date range.")
                    print(f"Total videos processed: {total_processed} | See debug/facebook_meetings.log for details")
                    
                finally:
                    page.close()
                    context.close()
                    browser.close()
                    
        except Exception as e:
            print(f"Error processing {base_url}: {e}")
            log_debug(f"[!] Critical error: {e}")
            return None
        
        return meetings_data