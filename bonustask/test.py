import asyncio
import json
import logging
import random
from playwright.async_api import async_playwright
from playwright_stealth import Stealth, ALL_EVASIONS_DISABLED_KWARGS

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug/logs.log'),
        logging.StreamHandler()
    ]
)

async def check_single_url_with_retry(browser_context, url, stealth, max_retries=2):
    """Check a single URL with retry logic"""
    for attempt in range(max_retries + 1):
        page = None
        try:
            page = await browser_context.new_page()
            
            # Set realistic viewport before navigation
            await page.set_viewport_size({"width": 1920, "height": 1080})
            
            # Navigate to URL first
            await page.goto(url, timeout=45000, wait_until='domcontentloaded')
            
            # Apply stealth mode AFTER navigation to avoid conflicts
            await stealth.apply_stealth_async(page)
            
            # Wait for either tr elements or timeout
            try:
                await page.wait_for_selector('tr', timeout=15000)
            except:
                # If no tr elements found, continue anyway
                pass
            
            # Wait for page to be more stable
            await page.wait_for_load_state('domcontentloaded', timeout=10000)
            
            # Smart scrolling with incremental delays
            try:
                # Get page height
                page_height = await page.evaluate("document.body.scrollHeight")
                viewport_height = 1080
                
                # Scroll in increments to trigger lazy loading
                for i in range(0, page_height, viewport_height // 2):
                    await page.evaluate(f"window.scrollTo(0, {i})")
                    await asyncio.sleep(random.uniform(0.5, 1.0))
                
                # Scroll back to top
                await page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(random.uniform(0.5, 1.0))
            except Exception as scroll_error:
                logging.debug(f"Scroll error for {url}: {scroll_error}")
            
            # Additional wait for JS-rendered content
            await asyncio.sleep(random.uniform(1.5, 2.5))
            
            # Check for tr elements
            tr_elements = await page.query_selector_all('tr')
            
            if tr_elements:
                logging.info(f"Found {len(tr_elements)} <tr> elements")
                return True
            else:
                logging.info("No <tr> elements found")
                return False
                
        except Exception as e:
            if attempt < max_retries:
                wait_time = random.uniform(2, 5) * (attempt + 1)
                logging.warning(f"Attempt {attempt + 1} failed for {url}: {e}. Retrying in {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)
            else:
                logging.error(f"All attempts failed for {url}: {e}")
                import traceback
                logging.error(f"Full traceback for {url}: {traceback.format_exc()}")
                return False
        
        finally:
            if page:
                await page.close()
                logging.debug(f"Closed page for {url}")
    
    return False

async def check_urls_for_tr_elements():
    # Read input JSON
    with open('data/input.json', 'r') as f:
        data = json.load(f)
    
    urls = data['base_urls']
    urls_with_tr = []
    
    # Configure stealth with realistic settings
    stealth = Stealth(
        navigator_languages_override=("en-US", "en"),
        navigator_platform="Win32",
        init_scripts_only=True
    )
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-background-timer-throttling',
                '--disable-renderer-backgrounding',
                '--disable-backgrounding-occluded-windows',
                '--disable-ipc-flooding-protection',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-default-apps',
                '--disable-popup-blocking'
            ]
        )
        
        for i, url in enumerate(urls):
            try:
                logging.info(f"Checking URL {i+1}/{len(urls)}: {url}")
                
                # Create fresh browser context for each URL to isolate everything
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='en-US',
                    timezone_id='America/New_York',
                    permissions=['geolocation'],
                    accept_downloads=False,
                    java_script_enabled=True,
                    ignore_https_errors=True
                )
                
                # Add realistic headers to context
                await context.set_extra_http_headers({
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'max-age=0'
                })
                
                # Check URL with retry logic
                has_tr_elements = await check_single_url_with_retry(context, url, stealth)
                
                if has_tr_elements:
                    urls_with_tr.append(url)
                
            except Exception as e:
                logging.error(f"Context creation failed for {url}: {e}")
                import traceback
                logging.error(f"Full traceback for {url}: {traceback.format_exc()}")
            
            finally:
                # Always close context to clean up resources
                try:
                    await context.close()
                    logging.debug(f"Closed context for {url}")
                except:
                    pass
            
            # Random delay between requests to avoid rate limiting
            if i < len(urls) - 1:  # Don't delay after last URL
                delay = random.uniform(1.5, 4.0)
                logging.debug(f"Waiting {delay:.1f}s before next URL...")
                await asyncio.sleep(delay)
        
        await browser.close()
    
    # Save results to output JSON
    output_data = {
        "urls_with_tr_elements": urls_with_tr,
        "total_count": len(urls_with_tr)
    }
    
    with open('data/output.json', 'w') as f:
        json.dump(output_data, f, indent=2)
    
    logging.info(f"Completed! Found {len(urls_with_tr)} URLs with <tr> elements")
    logging.info(f"Results saved to data/output.json")

if __name__ == "__main__":
    asyncio.run(check_urls_for_tr_elements())