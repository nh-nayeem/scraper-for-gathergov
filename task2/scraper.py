import json
import os
import yt_dlp
import requests
from urllib.parse import urlparse

# Configuration
INPUT_FILE = 'data/input.json'
OUTPUT_FILE = 'data/output.json'

def is_video_or_audio(url):
    """Check if URL points to a video or audio file."""
    video_extensions = ('.mp4', '.webm', '.mkv', '.avi', '.mov', '.flv', '.wmv')
    audio_extensions = ('.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac')
    
    parsed = urlparse(url)
    path = parsed.path.lower()
    
    return path.endswith(video_extensions) or path.endswith(audio_extensions)

def is_document(url):
    """Check if URL points to a document file."""
    document_extensions = ('.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', '.xlsx', '.ppt', '.pptx')
    return any(url.lower().endswith(ext) for ext in document_extensions)

def check_yt_dlp(url):
    """Check if URL can be processed by yt-dlp."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'simulate': True,  # Don't download, just check
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=False)
        return True
    except Exception:
        return False

def check_requests(url):
    """Check if URL can be accessed via requests."""
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        response.raise_for_status()
        return True
    except (requests.RequestException, ValueError):
        return False

def process_links():
    """Process links from input.json and save valid download URLs to output.json."""
    valid_urls = []
    os.makedirs('debug', exist_ok=True)  # Ensure debug directory exists
    
    try:
        # Read input file
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            links = json.load(f)
        
        # Open log file for writing
        with open('debug/log.txt', 'a', encoding='utf-8') as log_file:
            log_file.write("=== Log of added URLs ===\n")
            
            # Process each link
            for item in links:
                url = item.get('url', '').strip()
                link_type = item.get('type', '').lower()
                
                if not url:
                    print(f"Skipping empty URL in item: {item}")
                    continue
                
                try:
                    # Determine how to process the link
                    if link_type in ['video', 'audio'] or is_video_or_audio(url):
                        if check_yt_dlp(url):
                            valid_urls.append(url)
                            log_entry = f"Added: {url} (video/audio)\n"
                            log_file.write(log_entry)
                            print(f"✓ {log_entry.strip()}")
                        else:
                            print(f"✗ Skipped (yt-dlp failed): {url}")
                    elif link_type == 'document' or is_document(url):
                        if check_requests(url):
                            valid_urls.append(url)
                            log_entry = f"Added: {url} (document)\n"
                            log_file.write(log_entry)
                            print(f"✓ {log_entry.strip()}")
                        else:
                            print(f"✗ Skipped (requests failed): {url}")
                    else:
                        print(f"✗ Skipped (unsupported type): {url}")
                    
                except Exception as e:
                    error_msg = f"Error processing {url}: {str(e)}\n"
                    log_file.write(error_msg)
                    print(f"✗ {error_msg.strip()}")
            
            log_file.write(f"\nFound {len(valid_urls)} valid URLs out of {len(links)}\n")
            log_file.write("=== End of log ===\n\n")
        
        # Save only valid URLs to output file
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(valid_urls, f, indent=2)
            
        print(f"\nFound {len(valid_urls)} valid URLs out of {len(links)}")
        print(f"Results saved to {OUTPUT_FILE}")
        print(f"Log saved to debug/log.txt")
        
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {INPUT_FILE}")
    except FileNotFoundError:
        print(f"Error: File not found: {INPUT_FILE}")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    process_links()
