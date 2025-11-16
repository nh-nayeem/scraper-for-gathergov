from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from urllib.parse import urljoin
import requests
class DallasTxNewSwagitScraper:
    """Scraper dedicated to dallastx.new.swagit.com pages."""

    @staticmethod
    async def scrape(url: str, url_type: str) -> Optional[Dict[str, str]]:
        """
        Check if the URL matches the video page pattern and if it contains a download link.
        Return yt-dlp command if download link is found, otherwise return None.
        """
        if "dallastx.new.swagit.com/videos/" not in url:
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
        async with async_playwright() as p:
            browser = None
            try:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                page = await context.new_page()

                # Navigate to the video page
                print(f"Loading {url}...")
                await page.goto(url, wait_until="domcontentloaded", timeout=120000)
                await page.wait_for_load_state("networkidle")

                # Check for download link
                download_url = None
                page_content = await page.content()
                soup = BeautifulSoup(page_content, "html.parser")
                for link in soup.find_all('a', href=True):
                    if link['href'] == f"{url}/download":
                        download_url = urljoin(url, link['href'])
                        break
                if download_url:
                    return {
                        "url": download_url,
                        "command": f"yt-dlp -x --audio-format mp3 --audio-quality 0 {download_url}"
                    }
                return None

            except Exception as exc:
                print(f"Error processing {url}: {exc}")
                return None

            finally:
                if browser is not None:
                    await browser.close()