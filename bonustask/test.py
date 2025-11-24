import re
import requests

def get_google_drive_filename(view_url):
    """
    Extract the real file name from a Google Drive link
    without downloading the file.
    """

    # Extract file ID
    match = re.search(r"/file/d/([^/]+)/", view_url)
    if not match:
        raise ValueError("Invalid Google Drive view URL")
    
    file_id = match.group(1)

    # Convert to direct download URL
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

    # Make request (follow redirects)
    response = requests.get(download_url, allow_redirects=True, stream=True)

    # Get content disposition header
    cd = response.headers.get("Content-Disposition", "")
    if not cd:
        return None
    
    # Extract filename="..."
    filename_match = re.search(r'filename="([^"]+)"', cd)
    if filename_match:
        return filename_match.group(1)

    return None


# ----------------------------
# EXAMPLE USAGE
# ----------------------------

url = "https://drive.google.com/file/d/16TXOVQC4beEttNcIqLXHnLtVvk5lV1kh/view?usp=sharing"

filename = get_google_drive_filename(url)
print("Filename:", filename)