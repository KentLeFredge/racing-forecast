"""
IBOV Racing Forecast – Bulletin Generator
Fetches the Google Sheets calendar and produces a weekly bulletin.html
Run once manually or schedule weekly (e.g. every Monday morning).
"""

import csv
import io
import urllib.request
import urllib.error
from datetime import date, timedelta
import os
import sys

# ── CONFIG ──────────────────────────────────────────────────────────────────
SHEET_ID   = "1c4LrE84mqH_sw3yP3IwW6Yq45kI7hyh7G3pFVMihv58"
SHEET_URL  = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
OUTPUT     = os.path.join(os.path.dirname(__file__), "bulletin.html")

# Column layout in the CSV (0-indexed)
MONTHS = [
    'JANUARY','FEBRUARY','MARCH','APRIL','MAY','JUNE',
    'JULY','AUGUST','SEPTEMBER','OCTOBER','NOVEMBER','DECEMBER'
]
# Starting column index for each month's block
MONTH_OFFSETS = [0, 4, 8, 12, 16, 20, 24, 29, 33, 37, 41, 45]
# Columns per month block (JULY has 5 due to extra data column)
MONTH_WIDTHS  = [4, 4, 4, 4,  4,  4,  5,  4,  4,  4,  4,  3]

FR_DAY = {'LU': 'Monday', 'MA': 'Tuesday', 'ME': 'Wednesday',
          'JE': 'Thursday', 'VE': 'Friday', 'SA': 'Saturday', 'DI': 'Sunday'}

# Truly permanent / open-lobby series shown in the RIGHT column.
# Only list series that run every week regardless of the calendar.
# Scheduled one-off races come from the Google Sheet (left column only).
RECURRING = [
    ("THR GTC 60s",      "Each Sunday – 10 PM CET"),
    ("CVR F2 Cup",       "Every other Tuesday – 9 PM CEST"),
    ("RAC Supertourers", "24/7 – Open lobby Fridays"),
]

# ── CSV FETCH ────────────────────────────────────────────────────────────────
def fetch_csv() -> str:
    opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
    try:
        resp = opener.open(SHEET_URL, timeout=15)
        return resp.read().decode("utf-8")
    except Exception as e:
        print(f"[ERROR] Could not fetch Google Sheet: {e}", file=sys.stderr)
        sys.exit(1)

# ── CSV PARSE ────────────────────────────────────────────────────────────────
def parse_events(csv_text: str) -> dict:
    """Return {(month_0indexed, day_number): [event_str, ...]}"""
    events: dict = {}
    reader = csv.reader(io.StringIO(csv_text))
    rows   = list(reader)

    # rows[0] = filler/joke line
    # rows[1] = month headers
    # rows[2:] = day data (may span multiple CSV lines due to quoted newlines)
    for row in rows[2:]:
        if not row:
            continue
        for m_idx, (offset, width) in enumerate(zip(MONTH_OFFSETS, MONTH_WIDTHS)):
            if offset >= len(row):
                break
            day_abbr  = row[offset].strip()            if offset     < len(row) else ""
            event_raw = row[offset + 1].strip()        if offset + 1 < len(row) else ""
            day_s     = row[offset + 2].strip()        if offset + 2 < len(row) else ""
            if day_abbr and day_s:
                try:
                    day_n = int(day_s)
                except ValueError:
                    continue
                # An event cell can contain multiple events separated by newlines
                for evt in event_raw.splitlines():
                    evt = evt.strip()
                    if evt:
                        events.setdefault((m_idx, day_n), []).append(evt)
    return events

# ── WEEK SELECTION ───────────────────────────────────────────────────────────
def get_week_events(events: dict, anchor: date) -> list[dict]:
    """Return list of {date, weekday, event} for the Mon–Sun week of anchor."""
    monday = anchor - timedelta(days=anchor.weekday())
    week   = []
    for i in range(7):
        d   = monday + timedelta(days=i)
        key = (d.month - 1, d.day)
        for evt in events.get(key, []):
            week.append({"date": d, "weekday": d.strftime("%A"), "event": evt})
    return week

# ── HTML RENDERING ───────────────────────────────────────────────────────────
PARCHMENT_BG = "#c9aa82"
MAROON       = "#5c1a00"
DARK_BROWN   = "#6b3a1f"

def event_card_html(event: str, dt: date, weekday: str, join_link: str = "#") -> str:
    day_str = f"{weekday} {dt.day} {dt.strftime('%B')}"
    return f"""
    <div class="card">
      <div class="card-logo">
        <div class="logo-placeholder">LOGO</div>
      </div>
      <div class="card-info">
        <div class="series-name">{event}</div>
        <div class="event-date">{day_str}</div>
        <a class="join-link" href="{join_link}">Join link</a>
      </div>
    </div>"""

def recurring_card_html(name: str, schedule: str) -> str:
    return f"""
    <div class="card promo">
      <div class="card-logo">
        <div class="logo-placeholder">LOGO</div>
      </div>
      <div class="card-info">
        <div class="series-name">{name}</div>
        <div class="recurring">{schedule}</div>
      </div>
    </div>"""

def no_event_card() -> str:
    return """
    <div class="card empty">
      <div class="card-info" style="color:#aaa;font-style:italic;font-size:14px;padding:20px;">
        No scheduled event this week
      </div>
    </div>"""

def render_html(week_events: list[dict], week_label: str, year: int) -> str:
    # Build left-column cards (specific events), up to 3
    left_cards = ""
    used = week_events[:3]
    while len(used) < 3:
        used.append(None)
    for ev in used:
        if ev:
            left_cards += event_card_html(ev["event"], ev["date"], ev["weekday"])
        else:
            left_cards += no_event_card()

    # Build right-column cards (recurring series), up to 3
    right_cards = ""
    rec_used = RECURRING[:3]
    for name, sched in rec_used:
        right_cards += recurring_card_html(name, sched)

    # Interleave: left[0], right[0], left[1], right[1], left[2], right[2]
    grid_items = ""
    left_list  = [c for c in used]
    right_list = rec_used
    for i in range(3):
        if i < len(left_list):
            ev = left_list[i]
            if ev:
                grid_items += event_card_html(ev["event"], ev["date"], ev["weekday"])
            else:
                grid_items += no_event_card()
        if i < len(right_list):
            name, sched = right_list[i]
            grid_items += recurring_card_html(name, sched)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Racing Forecast – IBOV – {week_label}</title>
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@600;700&family=Crimson+Text:ital@1&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{
  background:{PARCHMENT_BG};
  background-image:radial-gradient(ellipse at center,#d4b88e 0%,#b8966a 100%);
  font-family:'Oswald',sans-serif;
  min-height:100vh;
  display:flex;align-items:center;justify-content:center;
  padding:20px;
}}
.page{{
  width:1280px;min-height:780px;
  background:linear-gradient(160deg,#d8bc90 0%,#c0985e 100%);
  padding:28px 55px 36px;
  position:relative;
  border:2px solid {DARK_BROWN};
  box-shadow:0 8px 32px rgba(0,0,0,.35);
}}
/* ── ornaments ── */
.side-ornaments{{
  position:absolute;top:50%;transform:translateY(-50%);
  display:flex;flex-direction:column;align-items:center;gap:6px;
  color:{DARK_BROWN};opacity:.65;
}}
.side-ornaments.left{{left:10px}}.side-ornaments.right{{right:10px}}
.orn-big{{font-size:40px}}.orn-sm{{font-size:18px}}
/* ── deco bar ── */
.deco-bar{{display:flex;align-items:center;gap:10px;margin:6px 0}}
.deco-bar .line{{flex:1;height:2px;background:{DARK_BROWN}}}
.deco-bar .gem{{font-size:18px;color:{DARK_BROWN}}}
/* ── header ── */
.header{{text-align:center;margin-bottom:16px}}
.header .presents{{
  font-family:'Crimson Text',serif;font-style:italic;
  font-size:22px;color:#5c2e0a;letter-spacing:.5px;
}}
.header h1{{
  font-family:'Oswald',sans-serif;font-size:74px;font-weight:700;
  color:{MAROON};text-transform:uppercase;letter-spacing:4px;line-height:1;
  text-shadow:2px 2px 0 rgba(0,0,0,.12);
}}
.week-label{{
  text-align:center;font-size:13px;font-weight:600;
  color:#5c2e0a;letter-spacing:3px;text-transform:uppercase;
  margin-bottom:16px;opacity:.75;
}}
/* ── grid ── */
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:13px;padding:0 28px}}
.card{{
  background:#fff;display:flex;align-items:stretch;
  min-height:125px;box-shadow:2px 3px 8px rgba(0,0,0,.2);
}}
.card.empty{{background:rgba(255,255,255,.45);min-height:80px;align-items:center}}
.card-logo{{
  width:105px;min-width:105px;background:#f0ede8;
  display:flex;align-items:center;justify-content:center;
  border-right:1px solid #e0d8cc;overflow:hidden;
}}
.card-logo img{{width:100%;height:100%;object-fit:contain;padding:8px}}
.logo-placeholder{{
  width:78px;height:78px;background:#ddd;border-radius:4px;
  display:flex;align-items:center;justify-content:center;
  font-size:9px;color:#999;text-align:center;padding:4px;
}}
.card-info{{
  flex:1;padding:12px 16px;display:flex;flex-direction:column;
  justify-content:center;gap:4px;
}}
.series-name{{
  font-family:'Oswald',sans-serif;font-size:19px;font-weight:700;
  color:#7a1a00;text-transform:uppercase;line-height:1.1;text-align:center;
}}
.event-date{{
  font-family:'Oswald',sans-serif;font-size:14px;font-weight:600;
  color:#2a2a2a;text-align:center;margin-top:5px;
}}
.join-link{{
  display:block;font-family:'Oswald',sans-serif;font-size:13px;
  font-weight:600;color:#1a5a9a;text-align:center;text-decoration:underline;
}}
.join-link:hover{{color:#0d3a6a}}
.recurring{{
  font-family:'Oswald',sans-serif;font-size:14px;font-weight:600;
  color:#2a2a2a;text-align:center;margin-top:5px;
}}
.footer{{
  text-align:center;margin-top:16px;
  font-family:'Crimson Text',serif;font-style:italic;
  font-size:12px;color:#5c2e0a;opacity:.65;letter-spacing:1px;
}}
</style>
</head>
<body>
<div class="page">
  <div class="side-ornaments left">
    <span class="orn-sm">✦</span>
    <span class="orn-big">&#10625;</span>
    <span class="orn-sm">✦</span>
  </div>
  <div class="side-ornaments right">
    <span class="orn-sm">✦</span>
    <span class="orn-big">&#10625;</span>
    <span class="orn-sm">✦</span>
  </div>

  <div class="deco-bar">
    <div class="gem">◆✦</div><div class="line"></div>
    <div class="gem">◆✦</div><div class="gem">✦◆</div>
    <div class="line"></div><div class="gem">✦◆</div>
  </div>

  <div class="header">
    <div class="presents">International Board of Vintage simracing presents :</div>
    <h1>Racing Forecast</h1>
  </div>

  <div class="week-label">Week of {week_label}</div>

  <div class="deco-bar" style="margin-bottom:14px">
    <div class="line"></div><div class="gem" style="font-size:13px">◆</div><div class="line"></div>
  </div>

  <div class="grid">
{grid_items}
  </div>

  <div class="deco-bar" style="margin-top:16px">
    <div class="gem">◆✦</div><div class="line"></div>
    <div class="gem">◆✦</div><div class="gem">✦◆</div>
    <div class="line"></div><div class="gem">✦◆</div>
  </div>

  <div class="footer">International Board of Vintage Simracing &mdash; {year}</div>
</div>
</body>
</html>"""

# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    today      = date.today()
    anchor     = today
    # If run on a weekend, forecast the current week; otherwise current week
    monday     = anchor - timedelta(days=anchor.weekday())
    sunday     = monday + timedelta(days=6)
    week_label = f"{monday.strftime('%B %d')} – {sunday.strftime('%B %d, %Y')}"

    print(f"[INFO] Fetching calendar from Google Sheets…")
    csv_text = fetch_csv()

    print(f"[INFO] Parsing events…")
    all_events = parse_events(csv_text)

    week_events = get_week_events(all_events, anchor)
    print(f"[INFO] Found {len(week_events)} event(s) for {week_label}:")
    for ev in week_events:
        print(f"       {ev['weekday']} {ev['date'].day}: {ev['event']}")

    html = render_html(week_events, week_label, today.year)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[OK]  Bulletin saved → {OUTPUT}")

if __name__ == "__main__":
    main()
