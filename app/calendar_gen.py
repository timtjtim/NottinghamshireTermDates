from datetime import date, timedelta

from icalendar import Calendar, Event


def generate_ics(academic_years: list[dict]) -> str:
    """
    Generate an ICS calendar from parsed term date data.

    Creates:
    - "School Term Time" all-day events for each term period
    - "School Holiday: <type>" all-day events for gaps between terms
    """
    cal = Calendar()
    cal.add("prodid", "-//Nottinghamshire Term Dates//EN")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", "Nottinghamshire School Term Dates")

    for year_data in academic_years:
        periods = year_data["periods"]
        terms = [p for p in periods if p["type"] == "term"]
        half_terms = [p for p in periods if p["type"] == "half_term"]

        # Create term time events
        for term in terms:
            # Extract season name from heading like "Autumn term 2025"
            season = term["term_name"].split(" ")[0]
            event = Event()
            event.add("summary", f"School Term Time: {season}")
            event.add("dtstart", term["start"])
            # ICS all-day events: DTEND is exclusive, so add 1 day
            event.add("dtend", term["end"] + timedelta(days=1))
            event.add("description", format_duration_description(term["start"], term["end"]))
            event.add("transp", "TRANSPARENT")
            cal.add_component(event)

        # Create holiday events from the gaps between terms
        holiday_events = compute_holidays(terms, half_terms, year_data)
        for holiday in holiday_events:
            event = Event()
            event.add("summary", f"School Holiday: {holiday['name']}")
            event.add("dtstart", holiday["start"])
            event.add("dtend", holiday["end"] + timedelta(days=1))
            event.add("description", format_duration_description(holiday["start"], holiday["end"]))
            event.add("transp", "TRANSPARENT")
            cal.add_component(event)

    # Compute summer holidays from gaps between academic years
    for i in range(len(academic_years) - 1):
        current_year = academic_years[i]
        next_year = academic_years[i + 1]

        current_terms = [p for p in current_year["periods"] if p["type"] == "term"]
        next_terms = [p for p in next_year["periods"] if p["type"] == "term"]

        if current_terms and next_terms:
            last_term = max(current_terms, key=lambda t: t["end"])
            first_term = min(next_terms, key=lambda t: t["start"])

            summer_start = last_term["end"] + timedelta(days=1)
            summer_end = first_term["start"] - timedelta(days=1)

            if summer_start <= summer_end:
                event = Event()
                event.add("summary", "School Holiday: Summer")
                event.add("dtstart", summer_start)
                event.add("dtend", summer_end + timedelta(days=1))
                event.add("description", format_duration_description(summer_start, summer_end))
                event.add("transp", "TRANSPARENT")
                cal.add_component(event)

    return cal.to_ical().decode("utf-8")


def compute_holidays(terms: list[dict], half_terms: list[dict], year_data: dict) -> list[dict]:
    """
    Compute holiday periods from the gaps between terms and from half-term entries.

    Holiday naming logic:
    - Half terms within Autumn/Spring/Summer → "<Term Name> Half term"
    - Gap between Autumn and Spring terms → "Christmas"
    - Gap between Spring and Summer terms → "Easter"
    - Gap after Summer term (before next year) → "Summer"
    """
    holidays = []

    # Half term holidays (explicitly listed on the page)
    for ht in half_terms:
        term_name = ht["term_name"].split(" ")[0]
        start = ht["start"]
        end = ht["end"]

        # Extend to include surrounding weekend
        if start.weekday() == 0:  # Monday → start on Saturday before
            start = start - timedelta(days=2)
        if end.weekday() == 4:  # Friday → end on Sunday after
            end = end + timedelta(days=2)

        holidays.append(
            {
                "name": f"{term_name} Half Term",
                "start": start,
                "end": end,
            }
        )

    # Sort terms by start date to find gaps between them
    sorted_terms = sorted(terms, key=lambda t: t["start"])

    for i in range(len(sorted_terms) - 1):
        current_term = sorted_terms[i]
        next_term = sorted_terms[i + 1]

        # The gap between end of current term and start of next term
        gap_start = current_term["end"] + timedelta(days=1)
        gap_end = next_term["start"] - timedelta(days=1)

        # Skip if this gap is already covered by a half term
        if any(ht["start"] >= gap_start and ht["end"] <= gap_end for ht in half_terms):
            continue

        # Determine holiday name based on which terms surround the gap
        holiday_name = classify_holiday_gap(current_term, next_term)

        if gap_start <= gap_end:
            holidays.append(
                {
                    "name": holiday_name,
                    "start": gap_start,
                    "end": gap_end,
                }
            )

    # No final summer holiday - we don't know when the next academic year starts

    return holidays


def classify_holiday_gap(current_term: dict, next_term: dict) -> str:
    """Classify the holiday between two terms based on their names."""
    current_name = current_term["term_name"].lower()
    next_name = next_term["term_name"].lower()

    if "autumn" in current_name and "spring" in next_name:
        return "Christmas"
    elif "spring" in current_name and "summer" in next_name:
        return "Easter"
    else:
        return "Summer"


def format_duration_description(start: date, end: date) -> str:
    """Format the duration description for an event."""
    # Calculate duration
    total_days = (end - start).days + 1  # inclusive
    weeks = total_days // 7
    days = total_days % 7

    parts = []
    if weeks:
        parts.append(f"{weeks} week{'s' if weeks != 1 else ''}")
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")

    return f"Duration: {', '.join(parts)}" if parts else "Duration: 1 day"
