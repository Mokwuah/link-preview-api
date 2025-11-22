import uvicorn
import os
import requests
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel, HttpUrl
from bs4 import BeautifulSoup
from typing import Optional
from urllib.parse import urljoin

app = FastAPI(title="Link Preview API")

# --- SECURITY CONFIGURATION ---
# 1. locally, this is "dev-secret", so you can test easily.
# 2. On Render/Cloud, we will set this to a strong password.
EXPECTED_SECRET = os.environ.get("API_SECRET", "dev-secret")

# --- DATA MODELS ---
class LinkMetadata(BaseModel):
    url: str
    title: Optional[str] = "No title found"
    description: Optional[str] = "No description found"
    image: Optional[str] = None
    favicon: Optional[str] = None  # <--- Added Feature

class LinkRequest(BaseModel):
    url: HttpUrl

# --- SECURITY FUNCTION ---
async def verify_secret(x_rapidapi_proxy_secret: str = Header(None, alias="X-RapidAPI-Proxy-Secret")):
    """
    Security Guard:
    Ensures the request actually came from RapidAPI (who handles the billing),
    and not a random person trying to bypass payment.
    """
    # Allow local testing
    if EXPECTED_SECRET == "dev-secret":
        return True
        
    # strict check for cloud deployment
    if x_rapidapi_proxy_secret == EXPECTED_SECRET:
        return True

    raise HTTPException(status_code=403, detail="Unauthorized: Access denied.")

# --- ENDPOINTS ---
@app.get("/")
def root():
    return {"status": "Online", "message": "Link Preview API is running"}

@app.post("/extract", response_model=LinkMetadata)
def extract_metadata(payload: LinkRequest, authorized: bool = Depends(verify_secret)):
    """
    Main Endpoint:
    1. Fetches the URL.
    2. Extracts OpenGraph (OG) tags and Favicon.
    3. Returns JSON.
    """
    try:
        # User-Agent is vital; otherwise sites like Google/Facebook reject the bot.
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; LinkBot/1.0)'}
        response = requests.get(str(payload.url), headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching URL: {str(e)}")

    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Helper to find tags safely
    def get_meta(attrs):
        tag = soup.find("meta", attrs=attrs)
        return tag.get("content") if tag else None

    # Extraction Logic
    title = get_meta({"property": "og:title"}) or (soup.title.string if soup.title else "No title")
    description = get_meta({"property": "og:description"}) or get_meta({"name": "description"})
    image = get_meta({"property": "og:image"})

    # --- FAVICON EXTRACTOR ---
    favicon = None
    # Look for standard icon tags
    icon_link = soup.find("link", rel="shortcut icon") or soup.find("link", rel="icon")
    if icon_link and icon_link.get("href"):
        # Resolve relative paths (e.g., "/icon.png" -> "https://site.com/icon.png")
        favicon = urljoin(str(payload.url), icon_link.get("href"))

    return {
        "url": str(payload.url),
        "title": title,
        "description": description,
        "image": image,
        "favicon": favicon
    }

# --- ENTRY POINT ---
if __name__ == "__main__":
    # Use the PORT environment variable (required for Render), default to 8000
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
