#!/usr/bin/env python3
"""Download cover images from Wikimedia URLs stored in referencias.json."""
import json, os, time, urllib.request

DATA = os.path.expanduser("~/Boti/aqui-hay-dragones/referencias.json")
COVERS = os.path.expanduser("~/Boti/aqui-hay-dragones/covers")
UA = "Mozilla/5.0 (compatible; AHD-Bot/1.0)"

os.makedirs(COVERS, exist_ok=True)
data = json.load(open(DATA))

total = data["total_references"]
dl = 0
skipped = 0
errors = 0

for ep in data["episodes"]:
    for ref in ep["references"]:
        url = ref.get("image", "")
        if not url:
            ref["cover"] = None
            continue
        
        # Generate local filename from URL
        fname = url.split("/")[-1]
        # Remove size prefix like 440px- for cleaner names
        local = os.path.join(COVERS, fname)
        
        if os.path.exists(local) and os.path.getsize(local) > 1000:
            ref["cover"] = f"covers/{fname}"
            skipped += 1
            continue
        
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=15) as resp:
                img_data = resp.read()
            if len(img_data) < 500:
                ref["cover"] = None
                errors += 1
                continue
            with open(local, "wb") as f:
                f.write(img_data)
            ref["cover"] = f"covers/{fname}"
            dl += 1
            print(f"  DL {fname[:50]} [{dl}/{total}]")
        except Exception as e:
            ref["cover"] = None
            errors += 1
            print(f"  ERR {fname[:40]}: {str(e)[:40]}")
        
        time.sleep(0.1)

# Save updated JSON with local cover paths
json.dump(data, open(DATA, "w"), ensure_ascii=False, indent=2)
print(f"\n=== DONE === Downloaded: {dl}, Skipped: {skipped}, Errors: {errors}, Total: {total}")
