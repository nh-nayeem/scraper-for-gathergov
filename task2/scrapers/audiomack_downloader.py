import subprocess
import asyncio
from playwright.async_api import async_playwright

TRACK_URL = "https://audiomack.com/pemberton-twp-planningzoning-board-meetings/song/678668c3069f2"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # must be visible
        context = await browser.new_context()
        page = await context.new_page()

        print("[*] Loading page...")
        await page.goto(TRACK_URL, timeout=0)

        # Wait for play button
        print("[*] Waiting for Play button…")
        await page.wait_for_selector("button[data-amlabs-play-button='true']")

        # Click Play (2 clicks sometimes required)
        print("[*] Clicking Play…")
        await page.click("button[data-amlabs-play-button='true']")

        audio_url = None

        # Detect m4a / m3u8 / cf requests
        def handle_response(res):
            url = res.url
            if ".m4a" in url or ".m3u8" in url:
                nonlocal audio_url
                audio_url = url
                print(f"[+] Audio URL found: {audio_url}")

        page.on("response", handle_response)

        print("[*] Waiting for stream link…")
        for _ in range(40):     # wait up to ~20 sec
            if audio_url:
                break
            await asyncio.sleep(0.5)

        if not audio_url:
            print("[-] ERROR: Could not capture audio stream!")
            await browser.close()
            return

        print("[*] Downloading with yt-dlp…")

        # Download raw M4A
        subprocess.run([
            "yt-dlp",
            "-o", "%(title)s.%(ext)s",
            audio_url
        ])

        # Convert to MP3 (optional):
        # subprocess.run(["yt-dlp", "-x", "--audio-format", "mp3", audio_url])

        print("[✓] Download complete!")

        await browser.close()

asyncio.run(main())
