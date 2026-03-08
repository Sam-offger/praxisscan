import csv, gspread
from pathlib import Path
from gspread.auth import local_server_flow

SHEET_NAME = "PraxisScan Leads"

COLUMNS = [
    "domain", "practice_name", "city", "country",
    "total_score", "score_tier",
    "positioning", "outreach_angle", "summary",
    "pain_points", "service_focus",
    "emails", "phones",
    "hiring_signal", "tracking_tags", "social_links",
    "affinity_score", "affinity_signals",
]

def load_csv(path):
    p = Path(path)
    if not p.exists() or p.stat().st_size < 10:
        return []
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))

def upload_tab(sheet, tab_name, data, color):
    if not data:
        print(f"  ⚠ {tab_name}: keine Daten")
        return
    header = COLUMNS
    rows = [header] + [[str(row.get(c, "")) for c in COLUMNS] for row in data]
    try:
        ws = sheet.worksheet(tab_name)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title=tab_name, rows=500, cols=len(COLUMNS))
    ws.update(rows)
    ws.format(f"A1:{chr(64+len(COLUMNS))}1", {
        "backgroundColor": color,
        "textFormat": {"bold": True, "foregroundColor": {"red":1,"green":1,"blue":1}},
    })
    print(f"  ✓ {tab_name}: {len(data)} Leads")

def main():
    print("🔐 Browser öffnet sich für Google Login...")
    client = gspread.oauth()  # Öffnet Browser-Login

    try:
        sheet = client.open(SHEET_NAME)
    except gspread.SpreadsheetNotFound:
        sheet = client.create(SHEET_NAME)

    top    = load_csv("exports/leads_top.csv")
    review = load_csv("exports/review_queue.csv")
    all_   = load_csv("exports/leads_all.csv")

    print("\n📊 Uploading...")
    upload_tab(sheet, "🏆 Top Leads",    top,    {"red":0.13,"green":0.55,"blue":0.13})
    upload_tab(sheet, "👀 Review Queue", review, {"red":0.9,"green":0.6,"blue":0.0})
    upload_tab(sheet, "📋 Alle Leads",   all_,   {"red":0.2,"green":0.2,"blue":0.6})

    url = f"https://docs.google.com/spreadsheets/d/{sheet.id}"
    print(f"\n✅ Fertig!")
    print(f"🔗 {url}")

if __name__ == "__main__":
    main()
