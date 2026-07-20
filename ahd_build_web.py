#!/usr/bin/env python3
"""
Aquí hay Dragones — Web Builder
Builds the web JSON from REFERENCIAS_COMPLETAS.json
Usage: python3 ahd_build_web.py
"""

import json, os, sys
from pathlib import Path

BASE = Path.home() / "Boti" / "aqui-hay-dragones"
REFS_JSON = BASE / "REFERENCIAS_COMPLETAS.json"
WEB_JSON = BASE / "referencias.json"
COVER_CACHE = BASE / "cover_cache.json"

CAT_EMOJIS = {
    "🎬": "Cine",
    "📺": "TV", 
    "📚": "Libros",
    "📖": "Cómics",
    "🎵": "Música",
    "🎮": "Videojuegos",
}


def main():
    if not REFS_JSON.exists():
        print(f"ERROR: {REFS_JSON} not found. Run ahd_extract.py first.")
        sys.exit(1)
    
    data = json.loads(REFS_JSON.read_text())
    
    # Load cover cache if exists
    covers = {}
    if COVER_CACHE.exists():
        covers = json.loads(COVER_CACHE.read_text())
    
    web_data = {
        "episodes": [],
        "total_episodes": 0,
        "total_references": 0,
    }
    
    for ep in data.get("episodes", []):
        web_ep = {
            "episode": ep["episode"],
            "references": [],
        }
        for ref in ep.get("references", []):
            cat = ref.get("category", "📄")
            if cat not in CAT_EMOJIS:
                continue  # Skip non-standard categories
            
            title = ref.get("title", "")
            author = ref.get("author", "")
            
            # Get cover from cache
            cover_key = f"{title}|{author}"
            image = covers.get(cover_key, "")
            
            web_ref = {
                "id": 0,  # Will be recalculated
                "title": title,
                "author": author,
                "category": cat,
                "amazon_url": ref.get("amazon_url", "#"),
                "image": image,
                "desc": ref.get("desc", ""),
            }
            web_ep["references"].append(web_ref)
        
        if web_ep["references"]:
            web_data["episodes"].append(web_ep)
    
    # Assign sequential IDs
    ref_id = 0
    for ep in web_data["episodes"]:
        for ref in ep["references"]:
            ref["id"] = ref_id
            ref_id += 1
    
    web_data["total_episodes"] = len(web_data["episodes"])
    web_data["total_references"] = ref_id
    
    WEB_JSON.write_text(json.dumps(web_data, ensure_ascii=False, indent=2))
    
    print(f"Web JSON built:")
    print(f"  Episodes: {web_data['total_episodes']}")
    print(f"  References: {web_data['total_references']}")
    print(f"  With covers: {sum(1 for ep in web_data['episodes'] for r in ep['references'] if r['image'])}")
    print(f"  With descriptions: {sum(1 for ep in web_data['episodes'] for r in ep['references'] if r.get('desc'))}")
    print(f"\nSaved to {WEB_JSON}")


if __name__ == "__main__":
    main()
