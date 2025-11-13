import yt_dlp
from datetime import datetime, timezone
import requests

def human(dt):
    if isinstance(dt, (int, float)):
        # epoch seconds -> ISO
        return datetime.fromtimestamp(dt, tz=timezone.utc).isoformat()
    if isinstance(dt, str) and dt.isdigit() and len(dt) == 8:
        # yyyymmdd -> ISO
        return datetime.strptime(dt, "%Y%m%d").date().isoformat()
    return str(dt)

def get_video_dates(url: str):
    dates = {}
    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
        info = ydl.extract_info(url, download=False)

    # Common date fields yt-dlp may expose
    for k in [
        "upload_date",         # yyyymmdd
        "release_date",        # yyyymmdd
        "timestamp",           # epoch seconds
        "release_timestamp",   # epoch seconds
        "modified_date",       # yyyymmdd
        "created_date",        # yyyymmdd
    ]:
        if info.get(k) is not None:
            dates[k] = human(info[k])

    # Optional: try HEAD on a media URL to get Last-Modified (server metadata)
    # (no download; just metadata)
    fmts = info.get("formats") or []
    best = next((f for f in fmts if f.get("url")), None)
    if best:
        try:
            head = requests.head(best["url"], allow_redirects=True, timeout=10)
            lm = head.headers.get("Last-Modified")
            if lm:
                dates["http_last_modified"] = lm
        except requests.RequestException:
            pass

    return info.get("title"), dates

if __name__ == "__main__":
    url = "https://dallastx.new.swagit.com/videos/320946"
    title, dates = get_video_dates(url)
    print("Title:", title)
    if dates:
        for k, v in dates.items():
            print(f"{k}: {v}")
    else:
        print("No date fields found.")
