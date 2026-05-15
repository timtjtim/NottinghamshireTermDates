import logging
import re
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

URL = "https://www.nottinghamshire.gov.uk/education/school-holidays-and-closures/school-holiday-and-term-dates"


def scrape_term_dates() -> list[dict]:
    """
    Scrape the Nottinghamshire term dates page and return structured data.

    Returns a list of academic years, each containing a list of periods
    (terms and holidays) with start/end dates and type info.
    """
    logger.debug("Fetching %s", URL)
    response = requests.get(
        URL,
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        },
    )
    response.raise_for_status()
    logger.debug("Page fetched: %d bytes, status %d", len(response.text), response.status_code)

    soup = BeautifulSoup(response.text, "html.parser")
    results = parse_academic_years(soup)
    logger.debug("Parsed %d academic years", len(results))
    return results


def parse_academic_years(soup: BeautifulSoup) -> list[dict]:
    """Parse all academic year sections from the page."""
    academic_years = []

    # Each academic year is in a collapse div
    buttons = soup.find_all("button", class_="item-heading")
    logger.debug("Found %d accordion buttons on page", len(buttons))

    for btn in buttons:
        title = btn.get_text(strip=True)
        if "School term dates" not in title:
            continue

        # Extract the year range from the title
        year_match = re.search(r"(\d{4})\s+to\s+(\d{4})", title)
        if not year_match:
            continue

        start_year = int(year_match.group(1))
        end_year = int(year_match.group(2))

        # Find the associated content panel
        target_id = (btn.get("data-bs-target") or "").lstrip("#")
        if not target_id:
            continue

        content_div = soup.find(id=target_id)
        if not content_div:
            continue

        periods = parse_year_content(content_div, start_year, end_year)
        if periods:
            logger.debug(
                "  %s: %d periods (%d terms, %d half terms)",
                title,
                len(periods),
                sum(1 for p in periods if p["type"] == "term"),
                sum(1 for p in periods if p["type"] == "half_term"),
            )
            for p in periods:
                logger.debug("    %s: %s to %s (%s)", p["type"], p["start"], p["end"], p.get("term_name", ""))
            academic_years.append(
                {
                    "title": title,
                    "start_year": start_year,
                    "end_year": end_year,
                    "periods": periods,
                }
            )

    return academic_years


def parse_year_content(content_div, start_year: int, end_year: int) -> list[dict]:
    """Parse the content of one academic year section into term/holiday periods."""
    periods = []

    # Find all h3 headings for terms (Autumn, Spring, Summer)
    headings = content_div.find_all("h3")

    for heading in headings:
        heading_text = heading.get_text(strip=True)

        # Skip non-term headings (like "Download this calendar" or "View calendar")
        if "term" not in heading_text.lower():
            continue

        # Get the list items following this heading
        ul = heading.find_next_sibling("ul")
        if not ul:
            continue

        items = ul.find_all("li")
        for item in items:
            text = item.get_text(separator=" ", strip=True)
            # Clean up extra whitespace
            text = re.sub(r"\s+", " ", text)

            period = parse_period_line(text, heading_text)
            if period:
                periods.append(period)

    return periods


def parse_period_line(text: str, term_heading: str) -> dict | None:
    """Parse a single line like 'Term time: Monday, 1 September 2025 to Friday, 17 October 2025 (7 weeks)'."""

    # Match "Term time: <date> to <date> (<duration>)"
    term_match = re.match(
        r"Term time:\s*(.+?)\s+to\s+(.+?)\s*\(([^)]+)\)",
        text,
    )
    if term_match:
        start_str = term_match.group(1).strip()
        end_str = term_match.group(2).strip()
        duration_str = term_match.group(3).strip()

        start_date = parse_date(start_str)
        end_date = parse_date(end_str)

        if start_date and end_date:
            return {
                "type": "term",
                "start": start_date,
                "end": end_date,
                "duration": duration_str,
                "term_name": term_heading,
            }

    # Match "Half term: <date> to <date>"
    half_term_match = re.match(
        r"Half term:\s*(.+?)\s+to\s+(.+?)$",
        text,
    )
    if half_term_match:
        start_str = half_term_match.group(1).strip()
        end_str = half_term_match.group(2).strip()

        start_date = parse_date(start_str)
        end_date = parse_date(end_str)

        if start_date and end_date:
            return {
                "type": "half_term",
                "start": start_date,
                "end": end_date,
                "term_name": term_heading,
            }

    return None


def parse_date(date_str: str) -> date | None:
    """Parse a date string like 'Monday, 1 September 2025' or 'Monday, 1 September'."""
    # Remove day name prefix if present
    date_str = re.sub(r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s*", "", date_str)
    # Clean up any extra whitespace
    date_str = re.sub(r"\s+", " ", date_str).strip()

    # Try full date: "1 September 2025"
    try:
        return datetime.strptime(date_str, "%d %B %Y").date()
    except ValueError:
        pass

    # Try without year (shouldn't happen for term time entries but just in case)
    try:
        # This won't have a year, so we can't reliably parse it
        return None
    except ValueError:
        pass

    return None
