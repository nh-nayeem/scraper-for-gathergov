class AudioMacScraper:
    async def scrape(self, url, url_type):
        if (url_type != "audio"):
            return None
        
        return {
            "url": url,
            "instruction": "use audiomack_downloader.py to download this audio"
        }