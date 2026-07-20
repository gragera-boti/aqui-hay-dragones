#!/usr/bin/env python3
"""
Fetch short descriptions from Wikipedia, using the same page-matching
strategy as the cover fetcher (checks for correct page, work-related names).
"""
import json, time, re, os
import urllib.request, urllib.parse

DATA_PATH = os.path.expanduser("~/Boti/todopoderosos/web/referencias.json")
CACHE_PATH = os.path.expanduser("~/Boti/todopoderosos/web/desc_cache.json")

UA = "TodopoderososBot/1.0 (descriptions-v2)"

WORK_WORDS = ["film", "movie", "novel", "book", "album", "comic", "tv series",
              "video game", "song", "studio album", "graphic novel", "manga",
              "television series", "crime drama", "American", "British",
              "Spanish", "directed by", "written by", "author", "singer",
              "musician", "band", "game", "franchise", "superhero", "animated"]

def rest_summary(title, lang="en"):
    api = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title, safe='')}"
    req = urllib.request.Request(api, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except:
        return None

def search_pages(query, lang="en", limit=3):
    api = f"https://{lang}.wikipedia.org/w/api.php"
    params = {"action":"query","list":"search","srsearch":query,"srprop":"snippet",
              "format":"json","origin":"*"}
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{api}?{qs}", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return [(p["pageid"], p["title"]) for p in data.get("query",{}).get("search",[])]
    except:
        return []

def page_matches(page_title, search_title):
    """Check if a Wikipedia page title is a reasonable match for our search."""
    pt = page_title.lower()
    st = search_title.lower()
    # Exact or partial match
    if st in pt or pt in st:
        return True
    # Split into words, check overlap
    st_words = set(re.sub(r'[^a-z0-9\s]', ' ', st).split())
    pt_words = set(re.sub(r'[^a-z0-9\s]', ' ', pt).split())
    # At least 50% of search words should be in page title
    if len(st_words) > 0:
        overlap = len(st_words & pt_words)
        if overlap >= max(2, len(st_words) // 2):
            return True
    return False

def clean_extract(text):
    """Clean and shorten Wikipedia extract."""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) <= 150:
        return text
    # Trim to ~150 chars ending at sentence boundary
    short = text[:200]
    for end in ['. ', '.\n', '! ', '? ']:
        idx = short.rfind(end)
        if idx > 30:
            return short[:idx+1]
    return short[:147] + '…'

def find_description(title, author=""):
    """Find a short description from Wikipedia, with quality checks."""
    clean = re.sub(r'\s*\(.*?\)\s*$', '', title).strip().strip('"\'«»')
    # Remove Spanish descriptive prefixes
    for prefix in ["La editorial ", "El libro ", "La película ", "La serie ",
                    "El cómic ", "La música ", "El videojuego ", "La obra ",
                    "El autor ", "El director ", "La novela ", "El álbum ",
                    "Los ", "Las ", "El ", "La "]:
        if clean.lower().startswith(prefix.lower()):
            clean = clean[len(prefix):].strip()
            break
    # Also remove trailing parenthetical descriptors
    clean = re.sub(r'\s*\(.*?\)\s*$', '', clean).strip()
    
    # Build queries with increasing specificity
    queries = []
    if author and author not in clean:
        queries.append(f"{clean} {author}")
    queries.append(clean)
    queries += [f"{clean} film", f"{clean} novel", f"{clean} (film)",
                f"{clean} album", f"{clean} (album)", f"{clean} TV series",
                f"{clean} video game", f"{clean} (novel)", f"{clean} comic"]
    
    for lang in ["en", "es"]:
        for query in queries:
            pages = search_pages(query, lang, limit=5)
            time.sleep(0.15)
            
            for pid, pt in pages:
                if not page_matches(pt, clean):
                    continue
                
                summary = rest_summary(pt, lang)
                time.sleep(0.1)
                
                if not summary or summary.get("type") != "standard":
                    continue
                
                desc = (summary.get("description") or "").strip()
                extract = (summary.get("extract") or "").strip()
                
                if not extract:
                    continue
                
                # Quality check: description should contain work-related words
                # or the page title should clearly match
                if desc:
                    has_work_words = any(w in desc.lower() for w in WORK_WORDS)
                else:
                    # No description - check if extract mentions the title
                    has_work_words = clean.lower() in extract.lower()[:200]
                
                if has_work_words or page_matches(pt, clean):
                    short_extract = clean_extract(extract)
                    return {"desc": desc, "extract": short_extract, "page": pt, "lang": lang}
    
    return None

def main():
    with open(DATA_PATH) as f:
        data = json.load(f)
    
    cache = {}
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            cache = json.load(f)
    
    total = sum(1 for ep in data["episodes"] for r in ep["references"])
    done = sum(1 for ep in data["episodes"] for r in ep["references"] if r.get("desc"))
    
    # Clear empty desc entries for retry
    cleared = 0
    for ep in data["episodes"]:
        for r in ep["references"]:
            if r.get("desc") and not r["desc"].strip():
                del r["desc"]
                cleared += 1
    if cleared:
        print(f"Cleared {cleared} empty desc entries for retry")
    
    print(f"Total: {total} | Already done: {done} | Cache: {len(cache)}")
    
    processed = 0
    found = 0
    not_found = 0
    batch = 0
    
    for ep in data["episodes"]:
        for ref in ep["references"]:
            if ref.get("desc"):
                processed += 1
                continue
            
            ckey = f"{ref['title']}|{ref.get('author','')}"
            if ckey in cache:
                if cache[ckey]:
                    ref["desc"] = cache[ckey]
                    found += 1
                else:
                    not_found += 1
                processed += 1
                continue
            
            result = find_description(ref["title"], ref.get("author",""))
            processed += 1
            batch += 1
            
            if result:
                ref["desc"] = result["extract"]
                cache[ckey] = result["extract"]
                found += 1
                d = result["desc"][:25] if result["desc"] else result["extract"][:25]
                status = f"✓ [{result['lang']}] {d:25s}"
            else:
                cache[ckey] = None
                not_found += 1
                status = "✗"
            
            print(f"  {status} [{processed}/{total}] {ref['category']} {ref['title'][:45]}")
            
            if batch >= 30:
                with open(DATA_PATH, "w") as f:
                    json.dump(data, f, ensure_ascii=False)
                with open(CACHE_PATH, "w") as f:
                    json.dump(cache, f, ensure_ascii=False)
                batch = 0
                print(f"    --- Saved: {found} found, {not_found} not found ---")
            
            time.sleep(0.3)
    
    with open(DATA_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, ensure_ascii=False)
    
    print(f"\n=== DONE === Found: {found} / Not found: {not_found}")

if __name__ == "__main__":
    main()
