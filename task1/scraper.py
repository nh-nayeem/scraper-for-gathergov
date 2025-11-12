from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List, Dict, Any
import json

class MeetingScraper:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.results = []
        
    def scrape(self) -> List[Dict[str, Any]]:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            start_date = self.config["start_date"]
            end_date = self.config["end_date"]
            for base_url in self.config["base_urls"]:
                result = {
                    "base_url": base_url,
                    "medias": []
                }
                try:
                    page = context.new_page()
                    print(f"Accessing {base_url}...")
                    page.goto(base_url, wait_until="domcontentloaded")
                    page.wait_for_load_state('networkidle', timeout=30000)
                    
                    # Get the page content after JavaScript execution
                    content = page.content()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Find all meeting rows with minutes
                    meetings = soup.select('tr.catAgendaRow')
                    
                    if not meetings:
                        print("No meeting rows found with class 'catAgendaRow'")
                        return self.results
                    
                    for meeting in meetings:
                        try:
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
                            from datetime import datetime
                            date_elem = meeting.select_one('td:first-child h3 strong')
                            date_str = date_elem.get_text(strip=True) if date_elem else ""
                            try :
                                date_obj = datetime.strptime(date_str,"%b%d, %Y")
                                date_str = date_obj.strftime("%Y-%m-%d")
                            except ValueError:
                                pass
                            
                            meeting_data = {
                                "meeting_url": video_url,  # Using YouTube video URL as meeting_url
                                "agenda_url": agenda_url,
                                "minutes_url": minutes_url,
                                "title": title,
                                "date": date_str
                            }
                            if (date_str >= start_date and date_str <= end_date):
                                result["medias"].append(meeting_data)
                            print(f"Found meeting: {title} - Minutes: {minutes_url}")
                            
                        except Exception as e:
                            print(f"Error processing meeting: {e}")
                            continue
                            
                    self.results.append(result)
                    
                except Exception as e:
                    print(f"Error processing {base_url}: {e}")
                    continue
                    
                finally:
                    page.close()
                    
            context.close()
            browser.close()
            
        return self.results

def load_config(file_path: str) -> Dict[str, Any]:
    """Load configuration from a JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)

def save_results(results: List[Dict[str, Any]], file_path: str) -> None:
    """Save results to a JSON file."""
    with open(file_path, 'w') as f:
        json.dump(results, f, indent=2)

def main():
    # Load configuration
    config = load_config('Data/input.json')
    
    # Run the scraper
    scraper = MeetingScraper(config)
    results = scraper.scrape()
    
    # Save results to output file with timestamp
    output_file = f'data/output.json'
    save_results(results, output_file)
    
    print(f"\nScraping complete. Results saved to {output_file}")
    print(f"Total meetings found: {sum(len(result['medias']) for result in results)}")

if __name__ == "__main__":
    main()