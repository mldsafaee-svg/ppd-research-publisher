"""PPD discovery and controlled Telegram publishing. Standard library only."""
import json, os, re, sys, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
QUEUE = ROOT / "data" / "sources.json"
SENT = ROOT / "data" / "sent.json"
CATALOGUE = ROOT / "data" / "research_catalogue.json"
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
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        # Only expose Telegram's safe diagnostic fields; never print the token-bearing URL.
        try:
            payload = json.loads(exc.read().decode('utf-8'))
        except (ValueError, UnicodeError):
            payload = {}
        description = str(payload.get('description', 'No description returned'))
        raise RuntimeError(f'Telegram/API HTTP {exc.code}: {description}') from None

def load(path, default):
    return json.loads(path.read_text("utf-8")) if path.exists() else default

def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", "utf-8")

def relevant_title(title):
    """Require explicit perinatal/postpartum mental-health relevance in title."""
    t = (title or "").casefold()
    return any(term in t for term in (
        "postpartum depression", "postnatal depression", "perinatal depression",
        "maternal mental health", "postpartum depressive", "postnatal depressive"))

def valid_year(year):
    return isinstance(year, int) and 1900 <= year <= datetime.now(timezone.utc).year

def catalogue_record(item):
    access = item.get('source_access') or 'metadata_only'
    return {
        'id': item.get('id'), 'title': item.get('title'), 'doi': item.get('doi'),
        'pmid': item.get('pmid'), 'openalex_id': item.get('openalex_id'),
        'discovered_via': item.get('discovered_via', []),
        'url': item.get('url'), 'year': item.get('year'),
        'evidence_level': access,
        'publication_status': 'approved' if eligible(item) else 'not_approved',
        'note_fa': ('فقط اطلاعات کتاب‌شناختی در دسترس است؛ متن کامل مطالعه نشده و هیچ یافته علمی از آن استخراج نشده است.'
                    if access == 'metadata_only' else 'سطح دسترسی منبع باید پیش از استناد بررسی شود.')
    }

def export_catalogue():
    entries = load(QUEUE, [])
    save(CATALOGUE, [catalogue_record(x) for x in entries])
    print('Catalogued records:', len(entries))

def source_key(item):
    doi = normalize_doi(item.get('doi'))
    if doi:
        return 'doi:' + doi
    pmid = str(item.get('pmid') or '').strip()
    if pmid:
        return 'pmid:' + pmid
    return 'url:' + str(item.get('url') or '').strip().lower()

def merge_candidate(old, new):
    result = dict(old)
    result['discovered_via'] = sorted(set(old.get('discovered_via', [])) | set(new.get('discovered_via', [])))
    for key in ('doi', 'pmid', 'title', 'url', 'year', 'abstract_en', 'openalex_id'):
        if not result.get(key) and new.get(key):
            result[key] = new[key]
    return result

def fetch_pubmed():
    base = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
    params = urllib.parse.urlencode({'db':'pubmed','term':'("postpartum depression"[Title] OR "postnatal depression"[Title] OR "perinatal depression"[Title]) AND 2024:3000[dp]','retmode':'json','retmax':25,'sort':'date'})
    ids = request_json(base + 'esearch.fcgi?' + params).get('esearchresult', {}).get('idlist', [])
    if not ids:
        return []
    q = urllib.parse.urlencode({'db':'pubmed','id':','.join(ids),'retmode':'json'})
    data = request_json(base + 'esummary.fcgi?' + q).get('result', {})
    items = []
    for pmid in ids:
        r = data.get(pmid, {})
        title = re.sub('<[^>]*>', '', r.get('title',''))
        if not relevant_title(title):
            continue
        doi = next((normalize_doi(x.get('value')) for x in r.get('articleids',[]) if x.get('idtype') == 'doi'), '')
        year_match = re.search(r'\b(19\d{2}|20\d{2})\b', r.get('pubdate',''))
        year = int(year_match.group(1)) if year_match else None
        if not valid_year(year):
            continue
        items.append({'pmid':pmid,'doi':doi,'title':title,'url':'https://pubmed.ncbi.nlm.nih.gov/'+pmid+'/', 'year':year,'discovered_via':['pubmed']})
    return items

def fetch_openalex():
    params = urllib.parse.urlencode({'search':'postpartum depression','filter':'from_publication_date:2024-01-01','per-page':25})
    data = request_json('https://api.openalex.org/works?' + params)
    items = []
    for r in data.get('results',[]):
        title = r.get('display_name','')
        if not relevant_title(title) or not valid_year(r.get('publication_year')):
            continue
        doi = normalize_doi(r.get('doi'))
        items.append({'doi':doi,'title':title,'url':r.get('doi') or r.get('id'),'year':r.get('publication_year'),'openalex_id':r.get('id'),'discovered_via':['openalex']})
    return items

def fetch_crossref():
    query = urllib.parse.urlencode({'query.title':'postpartum depression','rows':25,'sort':'published','order':'desc','filter':'from-pub-date:2024-01-01'})
    records = request_json('https://api.crossref.org/works?' + query).get('message',{}).get('items',[])
    items = []
    for r in records:
        title = (r.get('title') or [''])[0]
        year = (r.get('published',{}).get('date-parts') or [[None]])[0][0]
        if not relevant_title(title) or not valid_year(year):
            continue
        doi = normalize_doi(r.get('DOI'))
        items.append({'doi':doi,'title':title,'url':'https://doi.org/'+doi if doi else r.get('URL',''),'year':year,'discovered_via':['crossref']})
    return items

def discover():
    entries = load(QUEUE, [])
    index = {source_key(x): i for i,x in enumerate(entries) if source_key(x) != 'url:'}
    by_doi = {normalize_doi(x.get('doi')): i for i,x in enumerate(entries) if normalize_doi(x.get('doi'))}
    by_pmid = {str(x.get('pmid')): i for i,x in enumerate(entries) if x.get('pmid')}
    found = 0
    failures = []
    for name, fetcher in [('pubmed',fetch_pubmed),('crossref',fetch_crossref),('openalex',fetch_openalex)]:
        try:
            candidates = fetcher()
        except (RuntimeError, OSError, ValueError, KeyError) as exc:
            failures.append(name + ': ' + str(exc)[:180])
            continue
        for item in candidates:
            if not str(item.get('url','')).startswith('https://'):
                continue
            key = source_key(item)
            doi = normalize_doi(item.get('doi'))
            pmid = str(item.get('pmid') or '')
            i = by_doi.get(doi) if doi else None
            if i is None and pmid:
                i = by_pmid.get(pmid)
            if i is None:
                i = index.get(key)
            if i is not None:
                entries[i] = merge_candidate(entries[i],item)
                if doi: by_doi[doi] = i
                if pmid: by_pmid[pmid] = i
                continue
            entry = {'id':'PPD-'+str(len(entries)+1).zfill(5),**item,
                     'status':'discovered','summary_fa':'','limitations_fa':'',
                     'interpretation_fa':'','source_access':'metadata_only'}
            index[key] = len(entries)
            if doi: by_doi[doi] = len(entries)
            if pmid: by_pmid[pmid] = len(entries)
            entries.append(entry)
            found += 1
    save(QUEUE, entries)
    export_catalogue()
    print('New candidate sources:', found, 'Total:',len(entries))
    if failures:
        print('Source errors:', '; '.join(failures))
        if len(failures) == 3:
            raise RuntimeError('All source databases failed')

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
    elif cmd == 'catalogue':
        export_catalogue()
    elif cmd == "publish":
        publish()
    elif cmd == "test":
        publish(test=True)
    else:
        raise SystemExit("Use discover, publish or test")
