import uvicorn
import os
import requests
from fastapi import FastAPI, HTTPException, Header, Depends, Request
from pydantic import BaseModel, HttpUrl
from bs4 import BeautifulSoup
from typing import Optional
from urllib.parse import urljoin

app = FastAPI(title="Link Preview API")

# --- CONFIGURATION ---
EXPECTED_SECRET = os.environ.get("API_SECRET", "dev-secret")

# --- DATA MODELS ---
class LinkMetadata(BaseModel):
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    favicon: Optional[str] = None

class LinkRequest(BaseModel):
    url: HttpUrl

# --- DEBUGGING MIDDLEWARE ---
# This prints every request header to the logs so we can see what is arriving.
@app.middleware("http")
async def log_headers(request: Request, call_next):
    print(f"--- INCOMING REQUEST TO {request.url.path} ---")
    # Print all headers to find the secret
    for key, value in request.headers.items():
        if "secret" in key.lower():
            print(f"DEBUG HEADER FOUND: {key}: {value}")
    
    print(f"DEBUG: Server expects API_SECRET: '{EXPECTED_SECRET}'")
    response = await call_next(request)
    return response

# --- SECURITY FUNCTION ---
async def verify_secret(x_rapidapi_proxy_secret: str = Header(None, alias="X-RapidAPI-Proxy-Secret")):
    # 1. Check if secret matches
    if x_rapidapi_proxy_secret == EXPECTED_SECRET:
        return True
    
    # 2. If it failed, print WHY it failed
    print(f"!!! AUTH FAILURE !!!")
    print(f"Received: '{x_rapidapi_proxy_secret}'")
    print(f"Expected: '{EXPECTED_SECRET}'")
    
    # 3. Allow 'dev-secret' fallback if the server reset itself
    if EXPECTED_SECRET == "dev-secret":
        return True

    raise HTTPException(status_code=403, detail="Unauthorized: Access denied.")

# --- ENDPOINTS ---
@app.get("/")
def root():
    return {"status": "Online"}

@app.post("/extract", response_model=LinkMetadata)
def extract_metadata(payload: LinkRequest, authorized: bool = Depends(verify_secret)):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; LinkBot/1.0)'}
        response = requests.get(str(payload.url), headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching URL: {str(e)}")

    soup = BeautifulSoup(response.content, 'html.parser')
    
    def get_meta(attrs):
        tag = soup.find("meta", attrs=attrs)
        return tag.get("content") if tag else None

    title = get_meta({"property": "og:title"}) or (soup.title.string if soup.title else "No title")
    description = get_meta({"property": "og:description"}) or get_meta({"name": "description"})
    image = get_meta({"property": "og:image"})

    favicon = None
    icon_link = soup.find("link", rel="shortcut icon") or soup.find("link", rel="icon")
    if icon_link and icon_link.get("href"):
        favicon = urljoin(str(payload.url), icon_link.get("href"))

    return {
        "url": str(payload.url),
        "title": title,
        "description": description,
        "image": image,
        "favicon": favicon
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
