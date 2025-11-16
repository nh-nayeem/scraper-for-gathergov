from playwright.async_api import async_playwright
from typing import Optional, Any, Dict
import requests
class champdsScraper:
    def extract_m3u8(self, urls):
        for u in urls:
            if "index.m3u8" in u:
                return u.split("?")[0]  # remove query params
        return None
    
    async def scrape(self, url: str, url_type: str) -> Optional[Dict[str, str]]:
        if "champds.com" not in url:
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
                context = await browser.new_context()
                page = await context.new_page()

                captured_urls = []

            # capture all network requests
                page.on("request", lambda req: captured_urls.append(req.url))

                await page.goto(url)
                await page.wait_for_timeout(5000)  # allow player JS to load

                # optional: force the video to start loading by clicking play
                try:
                    await page.click("button.vjs-big-play-button")
                    await page.wait_for_timeout(5000)
                except:
                    pass

                m3u8_url = self.extract_m3u8(captured_urls)

                if m3u8_url:
                    cmd = f'''yt-dlp "{m3u8_url}" --add-header "Referer: https://play.champds.com/" --add-header "Origin: https://play.champds.com" --add-header "User-Agent: Mozilla/5.0" -x --audio-format mp3 o "guilderland_event_431.mp3"'''
                    return {
                        "url": m3u8_url,
                        "command": cmd
                    }
                else:
                    return None
            except Exception as exc:
                print(f"Error processing {url}: {exc}")
                return None
            finally:
                if browser is not None:
                    await browser.close()
            
