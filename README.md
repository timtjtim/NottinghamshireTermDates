# Nottinghamshire Term Dates

A service that scrapes the [Nottinghamshire County Council school holiday and term dates](https://www.nottinghamshire.gov.uk/education/school-holidays-and-closures/school-holiday-and-term-dates) page and generates a subscribable ICS calendar.

## Features

- Parses all available academic years from the council website
- Generates an ICS calendar with:
  - **School Term Time: Autumn/Spring/Summer** — all-day events covering each term period
  - **School Holiday: Christmas/Easter** — all-day events for breaks between terms
  - **School Holiday: Autumn/Spring/Summer Half Term** — all-day events for mid-term breaks
- Event descriptions include duration in weeks and days
- Results are cached for 24 hours to avoid unnecessary requests

## Running

```bash
docker compose up -d
```

The calendar is served at `http://localhost:8484/calendar.ics`.

## Subscribing in Google Calendar

1. Start the service on a publicly accessible host (or use a tunnel like ngrok)
2. In Google Calendar, go to **Settings → Add calendar → From URL**
3. Enter `http://<your-host>:8484/calendar.ics`

## Endpoints

| Path | Description |
|------|-------------|
| `/calendar.ics` | The ICS calendar feed |
| `/health` | Health check (returns `{"status": "ok"}`) |

## Development

Requires Python 3.12+.

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8484
```

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `CACHE_DIR` | `/app/cache` | Directory for cached calendar data |
