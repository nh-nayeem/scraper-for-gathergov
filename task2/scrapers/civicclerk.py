from typing import Optional, Dict
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from urllib.parse import urljoin
import requests
class civicclerkScraper:
    async def scrape(self, url: str, url_type: str) -> Optional[Dict[str, str]]:
        if "civicclerk" not in url:
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
        print(f"Loading {url}...")
        async with async_playwright() as p:
            browser = None
            try:
                browser = await p.chromium.launch(headless=False)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                page = await context.new_page()

                # Navigate to the video page
                print(f"Loading {url}...")
                await page.goto(url, wait_until="domcontentloaded", timeout=120000)
                await page.wait_for_load_state("networkidle")

                try:
                    await page.click("div.jw-icon-display[aria-label='Play']")
                    await page.wait_for_timeout(5000)
                except:
                    pass

                # Check for download link
                download_url = None
                page_content = await page.content()
                soup = BeautifulSoup(page_content, "html.parser")
                for link in soup.find_all('video', src=True):
                    print(link)
                    if '.mp4' in link['src']:
                        download_url = link['src']
                        print(download_url)
                        break
                if download_url:
                    return {
                        "url": download_url,
                        "command": f"yt-dlp {download_url} -x --audio-format mp3"
                    }
                return None

            except Exception as exc:
                print(f"Error processing {url}: {exc}")
                return None

            finally:
                if browser is not None:
                    await browser.close()