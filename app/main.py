import json
import logging
import os
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response

from app.scraper import scrape_term_dates
from app.calendar_gen import generate_ics

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI()

CACHE_ENABLED = os.environ.get("CACHE_ENABLED", "true").lower() == "true"
CACHE_DIR = Path(os.environ.get("CACHE_DIR", "/app/cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_MAX_AGE = 86400  # 24 hours


def get_cached_ics() -> str:
    cache_file = CACHE_DIR / "calendar.ics"
    cache_meta = CACHE_DIR / "cache_meta.json"

    if CACHE_ENABLED and cache_file.exists() and cache_meta.exists():
        meta = json.loads(cache_meta.read_text())
        age = time.time() - meta["timestamp"]
        if age < CACHE_MAX_AGE:
            logger.debug("Serving cached calendar (age: %.1f minutes)", age / 60)
            return cache_file.read_text()
        else:
            logger.debug("Cache expired (age: %.1f hours), regenerating", age / 3600)

    logger.debug("Scraping term dates from website")
    term_data = scrape_term_dates()
    logger.debug("Generating ICS calendar")
    ics_content = generate_ics(term_data)

    if CACHE_ENABLED:
        cache_file.write_text(ics_content)
        cache_meta.write_text(json.dumps({"timestamp": time.time()}))
        logger.debug("Cache written to %s", cache_file)

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
    logger.debug("Calendar endpoint hit")
    ics_content = get_cached_ics()
    return Response(content=ics_content, media_type="text/calendar")


@app.get("/health")
def health():
    return {"status": "ok"}
