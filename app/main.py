import json
import os
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response

from app.scraper import scrape_term_dates
from app.calendar_gen import generate_ics

app = FastAPI()

CACHE_DIR = Path(os.environ.get("CACHE_DIR", "/app/cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_MAX_AGE = 86400  # 24 hours


def get_cached_ics() -> str:
    cache_file = CACHE_DIR / "calendar.ics"
    cache_meta = CACHE_DIR / "cache_meta.json"

    if cache_file.exists() and cache_meta.exists():
        meta = json.loads(cache_meta.read_text())
        if time.time() - meta["timestamp"] < CACHE_MAX_AGE:
            return cache_file.read_text()

    # Scrape and regenerate
    term_data = scrape_term_dates()
    ics_content = generate_ics(term_data)

    cache_file.write_text(ics_content)
    cache_meta.write_text(json.dumps({"timestamp": time.time()}))

    return ics_content


@app.get("/", response_class=HTMLResponse)
def index():
    return """<h1>Nottinghamshire School Term Dates</h1>
<ul>
<li><a href="/calendar.ics">/calendar.ics</a> - Subscribable ICS calendar</li>
<li><a href="/health">/health</a> - Health check</li>
</ul>"""


@app.get("/calendar.ics")
def calendar():
    ics_content = get_cached_ics()
    return Response(content=ics_content, media_type="text/calendar")


@app.get("/health")
def health():
    return {"status": "ok"}
