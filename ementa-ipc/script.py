import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import os

URL = "https://www.ipc.pt/acao-social/alimentacao-cantinas-cafetarias/"
BASE = "https://www.ipc.pt"
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def get_latest_menus():
    r = requests.get(URL)
    soup = BeautifulSoup(r.text, "html.parser")
    
    menus = {"almoco": None, "jantar": None}

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if ".pdf" in href.lower():
            text = a.get_text(strip=True).lower()
            
            # Filter out ESTGOH and ensure it's a menu
            if "ementa" in text and "estgoh" not in text:
                full_url = urljoin(BASE, href)
                
                # Grab the first match for each meal type
                if "almoço" in text and not menus["almoco"]:
                    menus["almoco"] = full_url
                elif "jantar" in text and not menus["jantar"]:
                    menus["jantar"] = full_url
        
        # Stop searching once both are found
        if menus["almoco"] and menus["jantar"]:
            break

    if not menus["almoco"] and not menus["jantar"]:
        raise Exception("No menus found.")

    return menus

def download_and_send_to_discord(menus):
    files_to_send = {}
    opened_files = []
    downloaded_filenames = []
    
    try:
        # Download files
        for meal_type, url in menus.items():
            if url:
                r = requests.get(url)
                filename = f"ementa_{meal_type}.pdf"
                with open(filename, "wb") as f:
                    f.write(r.content)
                
                f_obj = open(filename, "rb")
                opened_files.append(f_obj)
                downloaded_filenames.append(filename)
                files_to_send[f"file_{meal_type}"] = (filename, f_obj, "application/pdf")
        
        # Send to Discord
        payload = {"content": "🍲 **Ementas da semana (Ficheiros anexados):**"}
        response = requests.post(WEBHOOK_URL, data=payload, files=files_to_send)
        
        if response.status_code not in (200, 204):
            raise Exception(f"Discord error: {response.status_code} - {response.text}")
            
    finally:
        # Close open file handlers and delete files locally
        for f in opened_files:
            f.close()
        for filename in downloaded_filenames:
            if os.path.exists(filename):
                os.remove(filename)

if __name__ == "__main__":
    if not WEBHOOK_URL:
        raise ValueError("Discord Webhook URL missing.")
    
    menus = get_latest_menus()
    for meal, url in menus.items():
        print(f"Found {meal}: {url}")
        
    download_and_send_to_discord(menus)
