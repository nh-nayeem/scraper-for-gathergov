from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import Dict, Any, List
from datetime import datetime

def scrape_url(page, base_url: str, start_date: str, end_date: str) -> List[Dict[str, str]]:
    """
    Scrape meeting data from City of Ventura website.
    
    Args:
        page: Playwright page object
        base_url: Base URL of the website
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        List of dictionaries containing meeting data
    """
    meetings_data = []
    
    try:
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
            return meetings_data
        
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
                date_elem = meeting.select_one('td:first-child h3 strong')
                date_str = date_elem.get_text(strip=True) if date_elem else ""
                try:
                    date_obj = datetime.strptime(date_str, "%b%d, %Y")
                    date_str = date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    continue  # Skip if date parsing fails
                
                # Only include meetings within the date range
                if date_str >= start_date and date_str <= end_date:
                    meeting_data = {
                        "meeting_url": video_url,
                        "agenda_url": agenda_url,
                        "minutes_url": minutes_url,
                        "title": title,
                        "date": date_str
                    }
                    meetings_data.append(meeting_data)
                    print(f"Found meeting: {title} - Minutes: {minutes_url}")
                
            except Exception as e:
                print(f"Error processing meeting: {e}")
                continue
                
    except Exception as e:
        print(f"Error processing {base_url}: {e}")
    
    return meetings_data