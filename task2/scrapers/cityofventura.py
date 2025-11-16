import requests
from typing import Optional, Dict

class cityofventuraScraper:
    async def scrape(self, url: str, url_type: str) -> Optional[Dict[str, str]]:
        if "cityofventura.ca.gov" not in url:
            return None
        if (url_type == "document"):
            r = requests.get(url)
            if r.status_code == 200:
                return {
                    "url": url,
                    "command": "use requests to download the file"
                }
            else:
                return None
        return None