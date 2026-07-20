#!/usr/bin/env python3
"""
Aquí hay Dragones — Reference Extractor
Extracts cultural references from SRT transcripts using DeepSeek API.
Usage: python3 ahd_extract.py
"""

import json, os, sys, re, time, textwrap
from pathlib import Path

BASE = Path.home() / "Boti" / "aqui-hay-dragones"
TRANS_DIR = BASE / "transcripts"
OUTPUT_FILE = BASE / "REFERENCIAS_COMPLETAS.md"
OUTPUT_JSON = BASE / "REFERENCIAS_COMPLETAS.json"
PROCESSED_FILE = BASE / "processed_srts.json"

# DeepSeek
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY")
if not DEEPSEEK_KEY:
    env_file = Path.home() / ".hermes" / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("DEEPSEEK_API_KEY="):
                DEEPSEEK_KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-chat"

# Amazon affiliate tag
AMAZON_TAG = "gragera-20"

CATEGORY_EMOJIS = {
    "🎬": "Cine",
    "📺": "TV",
    "📚": "Libros",
    "📖": "Cómics",
    "🎵": "Música",
    "🎮": "Videojuegos",
}

CATEGORIES_LIST = list(CATEGORY_EMOJIS.keys())


def load_processed():
    if PROCESSED_FILE.exists():
        return set(json.loads(PROCESSED_FILE.read_text()))
    return set()


def save_processed(processed):
    PROCESSED_FILE.write_text(json.dumps(sorted(processed), indent=2))


def call_llm(prompt, system=None, max_tokens=4096):
    if not DEEPSEEK_KEY:
        print("ERROR: DEEPSEEK_API_KEY not set")
        sys.exit(1)
    
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    import urllib.request
    payload = json.dumps({
        "model": MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.1,
    }).encode()
    
    req = urllib.request.Request(
        DEEPSEEK_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_KEY}",
        },
        method="POST",
    )
    
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read())
        content = data["choices"][0]["message"]["content"]
        # Handle DeepSeek thinking mode — strip think tags
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        return content
    except Exception as e:
        print(f"  LLM call failed: {e}")
        return None


def get_episode_title_from_srt(srt_path):
    """Derive episode title from SRT filename."""
    name = srt_path.stem
    name = re.sub(r'^AHD\s*', '', name)
    name = name.replace('_', ' ')
    name = re.sub(r'\s+', ' ', name).strip()
    return f"AHD {name}"


def split_into_chunks(text, max_chars=12000):
    """Split long transcript into chunks for processing."""
    # Try to split at sentence boundaries
    chunks = []
    current = ""
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        if len(current) + len(line) < max_chars:
            current += line + " "
        else:
            if current:
                chunks.append(current.strip())
            current = line + " "
    if current:
        chunks.append(current.strip())
    return chunks


def extract_system_prompt():
    return textwrap.dedent("""\
    Eres un crítico cultural experto que analiza transcripciones de podcasts.
    
    Tu tarea es extraer TODAS las referencias culturales mencionadas en la conversación.
    Incluye SOLO referencias que sean claramente identificables:
    - Películas (título + año de estreno + director si se menciona)
    - Series de TV
    - Libros (título + autor)
    - Cómics/Novelas gráficas
    - Música (canciones, álbumes, artistas, bandas)
    - Videojuegos
    
    NO incluyas: personas (actores, directores, escritores) como entidad separada,
    a menos que sean también una referencia cultural (ej: un libro de Stephen King).
    
    Incluye SOLO las que aparecen EXPLÍCITAMENTE mencionadas.
    NO adivines ni añadas contexto que no esté en el texto.
    """)


def extract_user_prompt(text):
    return textwrap.dedent(f"""\
    Analiza esta transcripción de un podcast español y extrae todas las referencias culturales.

    Para cada referencia, indica:
    1. Título (en español si tiene traducción conocida, sino en original)
    2. Tipo: usa UNO de estos emojis: {" ".join(CATEGORIES_LIST)}
       🎬 = Cine (películas)
       📺 = TV (series)
       📚 = Libros (novelas, ensayos, etc.)
       📖 = Cómics (novelas gráficas, manga, etc.)
       🎵 = Música (canciones, álbumes, artistas, bandas)
       🎮 = Videojuegos
    3. Autor/Director/Creador (si se menciona)
    
    Devuelve SOLO un array JSON. Nada más, ni explicaciones ni markdown.
    Formato: [{{"title": "...", "category": "🎬", "author": "..."}}, ...]
    
    Transcripción:
    {text[:14000]}
    """)


def load_existing_references():
    """Load existing references JSON if it exists."""
    if OUTPUT_JSON.exists():
        try:
            return json.loads(OUTPUT_JSON.read_text())
        except:
            pass
    return {"episodes": [], "total_episodes": 0, "total_references": 0}


def save_references(data):
    """Save references to both JSON and Markdown."""
    # Update counts
    data["total_episodes"] = len(data["episodes"])
    data["total_references"] = sum(len(ep.get("references", [])) for ep in data["episodes"])
    
    # Save JSON
    OUTPUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    
    # Save Markdown
    lines = ["# Referencias de Aquí hay Dragones\n"]
    lines.append(f"Total: {data['total_references']} referencias en {data['total_episodes']} episodios\n")
    lines.append("---\n")
    
    for ep in sorted(data["episodes"], key=lambda e: e.get("episode", ""), reverse=True):
        if not ep.get("references"):
            continue
        lines.append(f"\n## {ep['episode']}\n")
        for ref in ep["references"]:
            cat = ref.get("category", "📄")
            title = ref.get("title", "")
            author = ref.get("author", "")
            amazon = ref.get("amazon_url", "")
            author_str = f" · {author}" if author else ""
            amazon_str = f" · [Amazon]({amazon})" if amazon and amazon != "#" else ""
            lines.append(f"- {cat} **{title}**{author_str}{amazon_str}\n")
    
    OUTPUT_FILE.write_text("".join(lines))
    
    print(f"Saved: {data['total_references']} refs in {data['total_episodes']} eps")


def build_amazon_url(title, author=""):
    """Build an Amazon Spain search URL with affiliate tag."""
    query = title
    if author:
        query = f"{title} {author}"
    query_encoded = query.replace(' ', '+')
    return f"https://www.amazon.es/s?k={query_encoded}&tag={AMAZON_TAG}"


def parse_llm_response(content):
    """Parse the LLM response as JSON array."""
    # Try to extract JSON from the response
    # First, try direct JSON parse
    content = content.strip()
    
    # Remove markdown code fences if present
    content = re.sub(r'^```(?:json)?\s*', '', content)
    content = re.sub(r'\s*```$', '', content)
    
    try:
        refs = json.loads(content)
        if isinstance(refs, list):
            return refs
    except:
        pass
    
    # Try to find JSON array in the text
    match = re.search(r'\[.*?\]', content, re.DOTALL)
    if match:
        try:
            refs = json.loads(match.group(0))
            if isinstance(refs, list):
                return refs
        except:
            pass
    
    return []


def process_transcript(srt_path):
    """Extract references from one transcript."""
    text = srt_path.read_text(encoding='utf-8')
    episode_title = get_episode_title_from_srt(srt_path)
    print(f"\n{'='*60}")
    print(f"Processing: {episode_title}")
    print(f"  File: {srt_path.name}")
    print(f"  Size: {len(text):,} chars")
    
    # Split into chunks if needed
    chunks = split_into_chunks(text)
    print(f"  Chunks: {len(chunks)}")
    
    all_refs = []
    for i, chunk in enumerate(chunks):
        print(f"  Chunk {i+1}/{len(chunks)}...")
        response = call_llm(
            extract_user_prompt(chunk),
            system=extract_system_prompt(),
            max_tokens=4096,
        )
        if response:
            refs = parse_llm_response(response)
            print(f"    Found {len(refs)} references")
            all_refs.extend(refs)
        else:
            print(f"    Failed to process chunk {i+1}")
        
        # Rate limiting
        time.sleep(1.5)
    
    # Deduplicate references
    seen = set()
    unique_refs = []
    for ref in all_refs:
        key = (ref.get("title", ""), ref.get("category", ""))
        if key not in seen:
            seen.add(key)
            # Add Amazon URL
            title = ref.get("title", "")
            author = ref.get("author", "")
            ref["amazon_url"] = build_amazon_url(title, author)
            unique_refs.append(ref)
    
    return unique_refs


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract references from AHD transcripts")
    parser.add_argument("--srt", help="Process a specific SRT file")
    parser.add_argument("--all", action="store_true", help="Reprocess ALL SRTs")
    parser.add_argument("--check", action="store_true", help="Just list pending")
    args = parser.parse_args()
    
    srt_files = sorted(TRANS_DIR.glob("*.srt"))
    print(f"Found {len(srt_files)} SRT files in {TRANS_DIR}")
    
    if args.check:
        processed = load_processed()
        pending = [f for f in srt_files if f.stem not in processed]
        print(f"Processed: {len(processed)}, Pending: {len(pending)}")
        for f in pending:
            print(f"  - {f.name}")
        return
    
    if args.srt:
        srt_path = Path(args.srt)
        if not srt_path.exists():
            print(f"File not found: {srt_path}")
            sys.exit(1)
        srt_files = [srt_path]
    
    if args.all:
        processed = set()
    else:
        processed = load_processed()
    
    pending = [f for f in srt_files if f.stem not in processed]
    print(f"Already processed: {len(processed)}, Pending: {len(pending)}")
    
    if not pending:
        print("All transcripts processed!")
        return
    
    # Load existing references
    data = load_existing_references()
    existing_episodes = {ep["episode"]: ep for ep in data.get("episodes", [])}
    
    total_refs_added = 0
    
    for i, srt_path in enumerate(pending):
        refs = process_transcript(srt_path)
        
        episode_title = get_episode_title_from_srt(srt_path)
        
        # Add/update episode in data
        ep_entry = {
            "episode": episode_title,
            "references": refs,
        }
        
        if episode_title in existing_episodes:
            existing_episodes[episode_title] = ep_entry
        else:
            existing_episodes[episode_title] = ep_entry
        
        # Save progress
        processed.add(srt_path.stem)
        save_processed(processed)
        
        data["episodes"] = list(existing_episodes.values())
        save_references(data)
        
        total_refs_added += len(refs)
        print(f"\n  → Total added so far: {total_refs_added} references")
        
        # Rate limiting between episodes
        if i < len(pending) - 1:
            time.sleep(3)
    
    print(f"\n{'='*60}")
    print(f"DONE! Added {total_refs_added} references across {len(pending)} episodes")
    print(f"Total: {data['total_references']} references in {data['total_episodes']} episodes")


if __name__ == "__main__":
    main()
