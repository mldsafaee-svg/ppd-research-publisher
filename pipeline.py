"""PPD discovery and controlled Telegram publishing. Standard library only."""
import json, os, re, sys, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
QUEUE = ROOT / "data" / "sources.json"
SENT = ROOT / "data" / "sent.json"
API = "https://api.telegram.org/bot"

def normalize_doi(value):
    return re.sub(r"^https?://(?:dx\.)?doi\.org/", "", (value or "").strip(), flags=re.I).lower()

def eligible(item):
    return (item.get("status") == "approved" and bool(item.get("title")) and
            str(item.get("url", "")).startswith("https://") and bool(item.get("summary_fa")))

def format_message(item):
    fields = [f"مطالعات PPD | {item.get('id', 'منبع')}", item["title"],
              "خلاصه فارسی: " + item["summary_fa"]]
    if item.get("limitations_fa"):
        fields.append("محدودیت‌ها: " + item["limitations_fa"])
    if item.get("interpretation_fa"):
        fields.append("تحلیل پژوهشی: " + item["interpretation_fa"])
    fields += ["منبع اصلی: " + item["url"],
               "این متن خلاصه پژوهشی است؛ جایگزین تشخیص یا توصیه پزشکی نیست."]
    return "\n\n".join(fields)[:4000]

def request_json(url, payload=None):
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={
        "User-Agent": "PPD-Research-Library/1.0", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)

def load(path, default):
    return json.loads(path.read_text("utf-8")) if path.exists() else default

def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", "utf-8")

def discover():
    entries = load(QUEUE, [])
    existing = {normalize_doi(x.get("doi")) or x.get("url") for x in entries}
    query = urllib.parse.urlencode({"query.title": "postpartum depression",
        "rows": 15, "sort": "published", "order": "desc",
        "filter": "from-pub-date:2024-01-01"})
    response = request_json("https://api.crossref.org/works?" + query)
    count = 0
    for record in response.get("message", {}).get("items", []):
        doi = normalize_doi(record.get("DOI"))
        url = "https://doi.org/" + doi if doi else record.get("URL", "")
        if not url.startswith("https://") or (doi or url) in existing:
            continue
        title = (record.get("title") or [""])[0]
        if not title:
            continue
        entries.append({"id": "PPD-" + str(len(entries)+1).zfill(5),
                        "doi": doi, "title": title, "url": url,
                        "year": (record.get("published", {}).get("date-parts") or [[None]])[0][0],
                        "status": "discovered", "summary_fa": "",
                        "limitations_fa": "", "interpretation_fa": "",
                        "source_access": "metadata_only"})
        existing.add(doi or url)
        count += 1
    save(QUEUE, entries)
    print("New metadata-only candidates:", count)

def publish(test=False):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    channel = os.environ.get("TELEGRAM_CHANNEL_ID") or "@PPD_Research_FA"
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN secret is missing")
    if test:
        msg = "آزمون اتصال کانال مطالعات PPD — انتشار آزمایشی. این پیام محتوای پژوهشی نیست."
        response = request_json(API + token + "/sendMessage", {"chat_id": channel, "text": msg})
        if not response.get("ok"):
            raise RuntimeError("Telegram API did not confirm send")
        print("Test message confirmed, message_id:", response["result"]["message_id"])
        return
    sent = load(SENT, [])
    sent_set = set(sent)
    for item in load(QUEUE, []):
        key = item.get("doi") or item.get("url")
        if not eligible(item) or key in sent_set:
            continue
        response = request_json(API + token + "/sendMessage", {
            "chat_id": channel, "text": format_message(item),
            "disable_web_page_preview": True})
        if not response.get("ok"):
            raise RuntimeError("Telegram did not confirm send")
        sent.append(key)
        sent_set.add(key)
        save(SENT, sent)
        print("Published:", item["id"])

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "discover"
    if cmd == "discover":
        discover()
    elif cmd == "publish":
        publish()
    elif cmd == "test":
        publish(test=True)
    else:
        raise SystemExit("Use discover, publish or test")
