import os
import requests
from urllib.parse import urlparse

def download_file(url, save_dir='downloads', force_pdf=False):
    """
    Download a file from a URL to the specified directory.
    
    Args:
        url (str): The URL of the file to download
        save_dir (str): Directory to save the file (default: 'downloads')
        force_pdf (bool): If True, force save as PDF (default: False)
    
    Returns:
        str: Path to the downloaded file or None if download fails
    """
    try:
        # Create download directory if it doesn't exist
        os.makedirs(save_dir, exist_ok=True)
        
        # Send initial HEAD request to get content type
        head_response = requests.head(url, allow_redirects=True)
        content_type = head_response.headers.get('content-type', '').lower()
        
        # Get filename from URL or content-disposition header
        filename = os.path.basename(urlparse(url).path) or 'downloaded_file'
        content_disposition = head_response.headers.get('content-disposition', '')
        
        if 'filename=' in content_disposition:
            filename = content_disposition.split('filename=')[1].strip('"\'')
        
        # Ensure proper file extension
        if force_pdf or 'pdf' in content_type:
            if not filename.lower().endswith('.pdf'):
                filename = f"{os.path.splitext(filename)[0]}.pdf"
        
        # Send GET request to download the file
        with requests.get(url, stream=True) as response:
            response.raise_for_status()
            
            filepath = os.path.join(save_dir, filename)
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            print(f"✅ Successfully downloaded: {filepath}")
            return filepath
            
    except Exception as e:
        print(f"❌ Failed to download {url}: {str(e)}")
        return None

if __name__ == "__main__":
    # Example URLs to test
    test_urls = [
        "https://dallastx.new.swagit.com/videos/320946"
    ]
    
    for url in test_urls:
        print(f"\nDownloading: {url}")
        download_file(url, force_pdf=True)  # Force save as PDF