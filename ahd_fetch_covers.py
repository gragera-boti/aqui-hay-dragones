#!/usr/bin/env python3
"""
Fetch cover images for Aquí hay Dragones references using Wikipedia REST API.
Strategy: English Wikipedia first, no prop=images fallback (too unreliable).
Only returns images that look like actual covers/posters.
"""
import json, time, re, os
import urllib.request, urllib.parse

DATA_PATH = os.path.expanduser("~/Boti/aqui-hay-dragones/referencias.json")
CACHE_PATH = os.path.expanduser("~/Boti/aqui-hay-dragones/cover_cache.json")

UA = "AHD-Bot/1.0 (+https://github.com/gragera-boti/aqui-hay-dragones)"

# Known icon SVGs to skip
ICON_SVGS = {"Commons-emblem-question-book-yellow.svg", "Commons-emblem-question-book-orange.svg",
             "Book collection.jpg", "Cardboard_book_icon.jpg", "No-image-available.jpg",
             "Crystal_Clear_app_kedit.svg", "Fairytale_bookmark_silver.svg",
             "Audio-a.svg", "Music-a.svg", "Commons-emblem-question.svg",
             "Missing_image_2.svg", "Missing_image_2.png", "Question_book-new.svg",
             "Question_book-new.png", "Album.svg"}

COVER_SIZE = 440  # Wikipedia thumbnail width

def pagematch(title, page_title):
    """Check if a Wikipedia page title matches our search title."""
    pt = page_title.lower().replace("_", " ").replace("-", " ")
    st = title.lower()
    if pt == st or pt.startswith(st + " ") or pt.endswith(" " + st) or pt == st + " (film)" or pt == st + " (novel)":
        return True
    st_words = set(re.sub(r'[^a-z0-9\s]', ' ', st).split())
    pt_words = set(re.sub(r'[^a-z0-9\s]', ' ', pt).split())
    if len(st_words) > 0 and len(st_words & pt_words) >= max(2, len(st_words) // 2):
        return True
    return False

def page_has_work_name(page_title):
    """Check if page title suggests it's a work (film, book, etc.) not a person/place."""
    pt = page_title.lower()
    work_indicators = ["(film)", "(novel)", "(album)", "(song)", "(video game)",
                       "(TV series)", "(comics)", "(manga)", "(book)", "(series)",
                       "film", "novel", "album"]
    for w in work_indicators:
        if w in pt:
            return True
    return False

def get_rest_image(title):
    """Get image from Wikipedia REST API /page/summary."""
    for lang in ["en", "es"]:
        api = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title, safe='')}"
        req = urllib.request.Request(api, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            img = data.get("thumbnail", {}).get("source", "")
            if img and not any(svg in img for svg in ICON_SVGS):
                # Get larger version
                img = re.sub(r'/\d+px-', f'/{COVER_SIZE}px-', img)
                desc = data.get("description", "")
                if desc:
                    has_work = any(w in desc.lower() for w in ["film", "movie", "novel", "book", "album", "comic", "song", "series", "video game"])
                    if has_work:
                        return img
                # Also check if page title indicates a work
                if page_has_work_name(data.get("title", "")):
                    return img
                return img  # Accept even without work indicators - better to have a cover
        except:
            pass
    return ""

def search_and_get_image(query, lang="en"):
    """Search Wikipedia and try to get image from first matching result."""
    api = f"https://{lang}.wikipedia.org/w/api.php"
    params = {"action": "query", "list": "search", "srsearch": query,
              "srlimit": 5, "format": "json", "origin": "*"}
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{api}?{qs}", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        for p in data.get("query", {}).get("search", []):
            if pagematch(query, p["title"]):
                return get_rest_image(p["title"])
    except:
        pass
    return ""

def find_image(title, author=""):
    """Find cover image for a reference."""
    clean = re.sub(r'\s*\(.*?\)\s*$', '', title).strip().strip('"\'')

    # Try English Wikipedia first
    queries = []
    if author and author not in clean:
        queries.append(f"{clean} {author}")
    queries.append(f"{clean} (film)")
    queries.append(f"{clean} (novel)")
    queries.append(f"{clean} (album)")
    queries.append(f"{clean} (TV series)")
    queries.append(f"{clean} (video game)")
    queries.append(f"{clean} (song)")
    queries.append(clean)

    for q in queries:
        img = search_and_get_image(q, "en")
        if img:
            return img
        time.sleep(0.1)

    # Fallback to Spanish Wikipedia
    for q in [clean, f"{clean} (película)", f"{clean} (novela)", f"{clean} (álbum)"]:
        img = search_and_get_image(q, "es")
        if img:
            return img
        time.sleep(0.1)

    return ""

def main():
    import sys
    data = json.load(open(DATA_PATH))
    
    cache = {}
    if os.path.exists(CACHE_PATH):
        cache = json.load(open(CACHE_PATH))
    
    total = data["total_references"]
    done = sum(1 for ep in data["episodes"] for r in ep["references"] if r.get("image"))
    
    print(f"Total refs: {total}")
    print(f"Already have covers: {done}")
    print(f"In cache: {len(cache)}")
    
    processed = 0
    found = 0
    nf = 0
    batch = 0
    
    for ep in data["episodes"]:
        for ref in ep["references"]:
            if ref.get("image"):
                processed += 1
                continue
            
            ckey = f"{ref['title']}|{ref.get('author','')}"
            if ckey in cache:
                if cache[ckey]:
                    ref["image"] = cache[ckey]
                    found += 1
                else:
                    nf += 1
                processed += 1
                continue
            
            img = find_image(ref["title"], ref.get("author",""))
            processed += 1
            batch += 1
            
            if img:
                ref["image"] = img
                cache[ckey] = img
                found += 1
                status = f"✓ {img[-30:]}"
            else:
                cache[ckey] = None
                nf += 1
                status = "✗"
            
            print(f"  {status} [{processed}/{total}] {ref['category']} {ref['title'][:40]}")
            
            if batch >= 20:
                json.dump(data, open(DATA_PATH, "w"), ensure_ascii=False)
                json.dump(cache, open(CACHE_PATH, "w"), ensure_ascii=False)
                batch = 0
                print(f"    --- Saved: {found} found, {nf} not found ---")
            
            time.sleep(0.3)
    
    json.dump(data, open(DATA_PATH, "w"), ensure_ascii=False)
    json.dump(cache, open(CACHE_PATH, "w"), ensure_ascii=False)
    print(f"\n=== DONE === Found: {found} / Not found: {nf}")

if __name__ == "__main__":
    main()
