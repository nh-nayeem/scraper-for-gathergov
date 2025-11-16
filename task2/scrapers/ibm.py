import requests
from typing import Optional, Dict

class ibmScraper:
    async def scrape(self, url: str, url_type: str) -> Optional[Dict[str, str]]:
        if "video.ibm.com" not in url:
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
        if (url_type != "audio"):
            return None
        
        # Convert video URL to embed URL
        embed_link = url.replace("/recorded/", "/embed/recorded/") 
        return {
            "url": embed_link,
            "command": f'yt-dlp -x --audio-format mp3 --audio-quality 0 {embed_link}'
        }
