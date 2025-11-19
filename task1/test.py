import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.bethlehem-pa.gov/Calendar"
session = requests.Session()
BASE = "https://www.bethlehem-pa.gov"


# -----------------------------
# Extract hidden ASP.NET fields
# -----------------------------
def extract_hidden_fields(soup):
    data = {}
    for field in ["__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"]:
        tag = soup.find("input", {"name": field})
        if tag:
            data[field] = tag["value"]
    return data


# -----------------------------
# Extract EVENTARGUMENT (month switch)
# -----------------------------
def get_next_argument(soup):
    """
    Finds something like:
    javascript:__doPostBack('p$lt$ctl07$pageplaceholder$p$lt$ctl04$Calendar$calItems','V9405')
    """
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "__doPostBack" in href:
            # Extract the second argument
            try:
                arg = href.split(",")[1]
                arg = arg.replace(")", "").replace("'", "").strip()
                return arg
            except:
                continue
    return None


# -----------------------------
# Extract ALL events for 1 month
# -----------------------------
def extract_events(soup):
    events = []

    for div in soup.select("div.calendar-popup.modal"):
        event_id = div.get("id")            # e.g. data-449

        # Title
        h4 = div.find("h4")
        title = h4.get_text(strip=True) if h4 else None

        # Date / time / location info
        p_date = div.find("p", class_="popup-date")
        date_info = p_date.get_text(" ", strip=True) if p_date else None

        # Description (other <p> tags not including MORE link)
        desc_parts = []
        for p in div.find_all("p"):
            cls = p.get("class", [])
            if "popup-date" in cls or "marg-tp" in cls:
                continue
            desc_parts.append(p.get_text(" ", strip=True))
        description = " ".join(desc_parts) if desc_parts else None

        # MORE link
        more = div.select_one("p.marg-tp a[href]")
        if more:
            href = more["href"]
            if href.startswith("http"):
                url = href
            else:
                url = BASE + href
        else:
            url = None

        events.append({
            "id": event_id.replace("data-", "") if event_id else None,
            "title": title,
            "date_info": date_info,
            "description": description,
            "url": url
        })

    return events


# -----------------------------
# MAIN SCRAPER
# -----------------------------
def scrape_months(month_count=12):
    print("[*] Loading initial page...")
    resp = session.get(BASE_URL)
    soup = BeautifulSoup(resp.text, "lxml")

    all_events = []

    for i in range(month_count):
        print(f"\n==== MONTH {i+1} ====")

        # Extract events for this month
        events = extract_events(soup)
        print(f"[+] Found {len(events)} events")
        all_events.extend(events)

        # Prepare for next month
        hidden = extract_hidden_fields(soup)
        event_arg = get_next_argument(soup)

        if not event_arg:
            print("[!] No next-month argument found. Stopping.")
            break

        print(f"[*] Switching month via EVENTARGUMENT = {event_arg}")

        post_data = hidden.copy()
        post_data["__EVENTTARGET"] = "p$lt$ctl07$pageplaceholder$p$lt$ctl04$Calendar$calItems"
        post_data["__EVENTARGUMENT"] = event_arg

        # POSTBACK to load next month
        resp = session.post(BASE_URL, data=post_data)
        soup = BeautifulSoup(resp.text, "lxml")

    return all_events


# -----------------------------
# RUN SCRAPER
# -----------------------------
if __name__ == "__main__":
    events = scrape_months(month_count=12)

    print("\n=========== ALL EVENTS ===========")
    for e in events:
        print(
            f"{e['id']} | "
            f"{e['title']} | "
            f"{e['date_info']} | "
            f"{e['url']}"
        )
