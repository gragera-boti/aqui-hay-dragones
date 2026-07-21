#!/usr/bin/env python3
"""Build index.html + catalog.json for Aquí hay Dragones web."""
import json, os, re
from html import escape

DATA = os.path.expanduser("~/Boti/aqui-hay-dragones/referencias.json")
OUT = os.path.expanduser("~/Boti/aqui-hay-dragones/index.html")
JSON_OUT = os.path.expanduser("~/Boti/aqui-hay-dragones/catalog.json")

def resolve_cover(ref):
    """Return cover path: local if exists, else Wikipedia URL, else None."""
    # Check local cover first
    cover = ref.get("cover") or ""
    if cover and not cover.startswith("http") and os.path.exists(os.path.expanduser(f"~/Boti/aqui-hay-dragones/{cover}")):
        return cover
    # Fallback to Wikipedia URL
    image = ref.get("image") or ""
    if image:
        return image
    return None

os.makedirs(os.path.dirname(OUT), exist_ok=True)

data = json.load(open(DATA))
episodes = data["episodes"]
total_eps = data["total_episodes"]
total_refs = data["total_references"]

# Build catalog JSON for web
catalog = []
for ep in episodes:
    ep_name = ep["episode"]
    # Extract episode number
    m = re.match(r'AHD\s*(\d+)', ep_name)
    ep_num = int(m.group(1)) if m else 0
    
    for r in ep["references"]:
        catalog.append({
            "id": len(catalog),
            "title": r["title"],
            "author": r.get("author", ""),
            "category": r["category"],
            "episode": ep_name,
            "episode_num": ep_num,
            "episode_url": f"https://www.ivoox.com/podcast-aqui-hay-dragones_sq_f1900735_1.html",
            "cover": resolve_cover(r),
            "description": r.get("desc", ""),
            "amazon_url": r.get("amazon_url", ""),
            "episode_title_short": re.sub(r'^AHD\s*\d+\s*[–\-]\s*', '', ep_name)
        })

with open(JSON_OUT, "w") as f:
    json.dump(catalog, f, ensure_ascii=False)
print(f"Catalog: {len(catalog)} references written")

# ── Categories ──
category_icons = {
    "🎬": "cine", "📺": "tv", "📚": "libros",
    "📖": "comics", "🎵": "musica", "🎮": "videojuegos"
}
category_labels = {
    "🎬": "Cine", "📺": "TV", "📚": "Libros",
    "📖": "Cómics", "🎵": "Música", "🎮": "Videojuegos"
}

# Count per episode
ep_counter = {}
for r in catalog:
    ep = r["episode"]
    ep_counter[ep] = ep_counter.get(ep, 0) + 1

# Build HTML
def build_html():
    eps_html = ""
    catalog_idx = 0
    for i, ep in enumerate(episodes):
        ep_name = ep["episode"]
        m = re.match(r'AHD\s*(\d+)', ep_name)
        ep_num = int(m.group(1)) if m else 0
        short = re.sub(r'^AHD\s*\d+\s*[–\-]\s*', '', ep_name)
        count = ep_counter.get(ep_name, 0)
        
        refs_html = ""
        ref_id = 0
        for r in ep["references"]:
            cat = r["category"]
            label = category_labels.get(cat, cat)
            icon = category_icons.get(cat, cat)
            cover_html = ""
            cover_path = resolve_cover(r)
            if cover_path:
                cover_html = f'<div class="card-cover"><img src="{escape(cover_path)}" alt="{escape(r["title"])}" loading="lazy"></div>'
            refs_html += f'''\
            <div class="ref-card" data-category="{icon}" onclick="openModal({catalog_idx + ref_id})">
              {cover_html}
              <div class="card-badge {icon}">{label}</div>
              <div class="card-info">
                <div class="card-title">{escape(r["title"])}</div>
                {f'<div class="card-author">{escape(r.get("author", ""))}</div>' if r.get("author") else ''}
              </div>
            </div>'''
            ref_id += 1
        catalog_idx += ref_id
        
        ep_id = f"ep-{ep_num}"
        eps_html += f'''\
        <div class="episode-group" data-epnum="{ep_num}">
          <div class="episode-header" onclick="toggleEpisode('{ep_id}')">
            <div class="ep-number">AHD {ep_num}</div>
            <div class="ep-title">{escape(short)}</div>
            <div class="ep-count">{count}</div>
            <div class="ep-arrow">▼</div>
          </div>
          <div class="episode-body" id="{ep_id}">
            {refs_html}
          </div>
        </div>'''
    
    return f'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Aquí hay Dragones — Catálogo de Referencias</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🐉</text></svg>">
<style>
  :root {{
    --bg: #0a0a0f;
    --surface: #13131a;
    --surface2: #1a1a24;
    --border: #2a2a3a;
    --text: #e0dcd0;
    --text2: #8a8678;
    --gold: #c9a84c;
    --gold-dim: #8a7a3a;
    --gold-bright: #e8c85a;
    --gold-glow: rgba(201, 168, 76, 0.15);
    --radius: 8px;
    --radius-lg: 12px;
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
  }}
  .header {{
    background: linear-gradient(135deg, #0a0a0f 0%, #1a1a24 50%, #0a0a0f 100%);
    border-bottom: 1px solid var(--border);
    padding: 40px 20px 30px;
    text-align: center;
    position: relative;
    overflow: hidden;
  }}
  .header::before {{
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(ellipse at center, var(--gold-glow) 0%, transparent 60%);
    pointer-events: none;
  }}
  .header h1 {{
    font-size: 2.2rem;
    color: var(--gold);
    letter-spacing: 2px;
    position: relative;
    z-index: 1;
  }}
  .header h1 span {{ color: var(--gold-bright); }}
  .header p {{
    color: var(--text2);
    margin-top: 8px;
    font-size: 0.95rem;
    position: relative;
    z-index: 1;
  }}
  .header .stats {{
    margin-top: 12px;
    display: flex;
    justify-content: center;
    gap: 24px;
    position: relative;
    z-index: 1;
  }}
  .header .stats span {{
    color: var(--gold-dim);
    font-size: 0.85rem;
  }}
  .header .stats strong {{
    color: var(--gold);
    font-size: 1.1rem;
  }}
  
  /* Controls */
  .controls {{
    max-width: 1000px;
    margin: 20px auto 0;
    padding: 0 20px;
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    align-items: center;
  }}
  .search-box {{
    flex: 1;
    min-width: 200px;
    padding: 10px 16px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text);
    font-size: 0.95rem;
    outline: none;
    transition: border-color 0.2s;
  }}
  .search-box:focus {{ border-color: var(--gold-dim); }}
  .search-box::placeholder {{ color: var(--text2); }}
  .filter-group {{
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }}
  .filter-btn {{
    padding: 8px 14px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text2);
    cursor: pointer;
    font-size: 0.85rem;
    transition: all 0.2s;
  }}
  .filter-btn:hover {{ border-color: var(--gold-dim); color: var(--text); }}
  .filter-btn.active {{ background: var(--gold-dim); color: #000; border-color: var(--gold); }}
  
  /* Episode groups */
  .container {{
    max-width: 1100px;
    margin: 0 auto;
    padding: 10px 20px 60px;
  }}
  .episode-group {{
    margin-bottom: 4px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    transition: border-color 0.2s;
  }}
  .episode-group:hover {{ border-color: var(--gold-dim); }}
  .episode-header {{
    display: flex;
    align-items: center;
    padding: 14px 18px;
    background: var(--surface);
    cursor: pointer;
    user-select: none;
    gap: 12px;
    transition: background 0.2s;
  }}
  .episode-header:hover {{ background: var(--surface2); }}
  .ep-number {{
    font-weight: 700;
    color: var(--gold);
    min-width: 60px;
    font-size: 0.9rem;
  }}
  .ep-title {{
    flex: 1;
    color: var(--text);
    font-size: 0.9rem;
  }}
  .ep-count {{
    color: var(--text2);
    font-size: 0.8rem;
    min-width: 40px;
    text-align: right;
  }}
  .ep-arrow {{
    color: var(--gold-dim);
    transition: transform 0.3s;
    font-size: 0.8rem;
  }}
  .episode-body {{
    display: none;
    padding: 16px;
    background: var(--bg);
  }}
  .episode-body.open {{ display: block; }}
  .episode-group.open .ep-arrow {{ transform: rotate(180deg); }}
  
  /* Reference cards grid */
  .refs-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 12px;
  }}
  .ref-card {{
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    cursor: pointer;
    transition: all 0.2s;
    position: relative;
    overflow: hidden;
    min-height: 72px;
  }}
  .ref-card:hover {{
    border-color: var(--gold-dim);
    background: var(--surface2);
    transform: translateY(-1px);
  }}
  .card-cover {{
    width: 60px;
    height: 82px;
    flex-shrink: 0;
    border-radius: 4px;
    overflow: hidden;
    background: var(--surface2);
  }}
  .card-cover img {{
    width: 100%;
    height: 100%;
    object-fit: cover;
  }}
  .card-info {{
    flex: 1;
    min-width: 0;
  }}
  .card-title {{
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--text);
    line-height: 1.3;
  }}
  .card-author {{
    font-size: 0.78rem;
    color: var(--text2);
    margin-top: 3px;
  }}
  .card-badge {{
    position: absolute;
    top: 6px;
    right: 6px;
    font-size: 0.65rem;
    padding: 2px 7px;
    border-radius: 4px;
    background: rgba(0,0,0,0.6);
    color: var(--text2);
    backdrop-filter: blur(4px);
  }}
  .ref-card[data-category="cine"] .card-badge{{background:rgba(180,60,60,0.7);color:#fff}}
  .ref-card[data-category="tv"] .card-badge{{background:rgba(60,120,180,0.7);color:#fff}}
  .ref-card[data-category="libros"] .card-badge{{background:rgba(60,150,80,0.7);color:#fff}}
  .ref-card[data-category="comics"] .card-badge{{background:rgba(180,120,40,0.7);color:#fff}}
  .ref-card[data-category="musica"] .card-badge{{background:rgba(120,60,180,0.7);color:#fff}}
  .ref-card[data-category="videojuegos"] .card-badge{{background:rgba(40,160,180,0.7);color:#fff}}
  
  /* Modal */
  .modal-overlay {{
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.8);
    z-index: 1000;
    justify-content: center;
    align-items: center;
    backdrop-filter: blur(4px);
  }}
  .modal-overlay.open {{ display: flex; }}
  .modal {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    max-width: 500px;
    width: 90%;
    max-height: 85vh;
    overflow-y: auto;
    padding: 30px;
    position: relative;
    animation: fadeIn 0.2s;
  }}
  @keyframes fadeIn {{ from {{ opacity:0; transform:scale(0.95); }} to {{ opacity:1; transform:scale(1); }} }}
  .modal-close {{
    position: absolute;
    top: 12px;
    right: 16px;
    background: none;
    border: none;
    color: var(--text2);
    font-size: 1.5rem;
    cursor: pointer;
  }}
  .modal-close:hover {{ color: var(--text); }}
  .modal-cover {{
    width: 200px;
    height: 280px;
    margin: 0 auto 20px;
    border-radius: var(--radius);
    overflow: hidden;
    background: var(--surface2);
  }}
  .modal-cover img {{
    width: 100%;
    height: 100%;
    object-fit: cover;
  }}
  .modal-info {{ text-align: center; }}
  .modal-title {{
    font-size: 1.3rem;
    font-weight: 700;
    color: var(--gold);
    margin-bottom: 4px;
  }}
  .modal-author {{
    color: var(--text2);
    font-size: 0.9rem;
    margin-bottom: 16px;
  }}
  .modal-category {{
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.8rem;
    margin-bottom: 12px;
  }}
  .modal-desc {{
    color: var(--text);
    font-size: 0.88rem;
    line-height: 1.6;
    margin-bottom: 16px;
    text-align: left;
  }}
  .modal-episode {{
    font-size: 0.8rem;
    color: var(--text2);
    margin-bottom: 16px;
  }}
  .modal-amazon {{
    display: inline-block;
    padding: 10px 24px;
    background: var(--gold);
    color: #000;
    text-decoration: none;
    border-radius: var(--radius);
    font-weight: 600;
    font-size: 0.9rem;
    transition: all 0.2s;
  }}
  .modal-amazon:hover {{ background: var(--gold-bright); transform: translateY(-1px); }}
  
  /* Nav buttons */
  .modal-nav {{
    display: flex;
    justify-content: space-between;
    margin-top: 20px;
    gap: 12px;
  }}
  .modal-nav-btn {{
    padding: 8px 16px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text2);
    cursor: pointer;
    font-size: 0.85rem;
    transition: all 0.2s;
    flex: 1;
  }}
  .modal-nav-btn:hover {{ border-color: var(--gold-dim); color: var(--text); }}
  
  .no-results {{ color: var(--text2); text-align: center; padding: 40px; }}
  
  /* Stats animation */
  .stat-num {{ display: inline-block; }}
  .fade-in {{ animation: fadeIn 0.3s; }}
  
  @media (max-width: 640px) {{
    .header h1 {{ font-size: 1.5rem; }}
    .refs-grid {{ grid-template-columns: 1fr; }}
    .controls {{ flex-direction: column; }}
    .search-box {{ width: 100%; }}
    .filter-group {{ width: 100%; justify-content: center; }}
  }}
</style>
</head>
<body>
<div class="header">
  <h1>🐉 <span>Aquí hay Dragones</span></h1>
  <p>Catálogo de referencias culturales del podcast</p>
  <div class="stats">
    <span>📚 <strong>{total_eps}</strong> episodios</span>
    <span>🏷️ <strong>{total_refs}</strong> referencias</span>
  </div>
</div>

<div class="controls">
  <input type="text" class="search-box" id="search" placeholder="🔍 Buscar película, libro, autor..." oninput="filterRefs()">
  <div class="filter-group">
    <button class="filter-btn active" onclick="setFilter('all')">✨ Todas</button>
    <button class="filter-btn" onclick="setFilter('cine')">🎬 Cine</button>
    <button class="filter-btn" onclick="setFilter('tv')">📺 TV</button>
    <button class="filter-btn" onclick="setFilter('libros')">📚 Libros</button>
    <button class="filter-btn" onclick="setFilter('comics')">📖 Cómics</button>
    <button class="filter-btn" onclick="setFilter('musica')">🎵 Música</button>
    <button class="filter-btn" onclick="setFilter('videojuegos')">🎮 Juegos</button>
  </div>
</div>

<div class="container" id="episodes-list">
{eps_html}
</div>

<!-- Modal -->
<div class="modal-overlay" id="modal" onclick="if(event.target===this)closeModal()">
  <div class="modal" id="modalContent">
    <button class="modal-close" onclick="closeModal()">✕</button>
    <div id="modalBody"></div>
    <div class="modal-nav">
      <button class="modal-nav-btn" onclick="navModal(-1)">◀ Anterior</button>
      <button class="modal-nav-btn" onclick="navModal(1)">Siguiente ▶</button>
    </div>
  </div>
</div>

<script>
const catalog = {json.dumps(catalog, ensure_ascii=False)};
let currentFilter = 'all';
let currentId = 0;

function toggleEpisode(id) {{
  const body = document.getElementById(id);
  const group = body.closest('.episode-group');
  body.classList.toggle('open');
  group.classList.toggle('open');
}}

function filterRefs() {{
  const q = document.getElementById('search').value.toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g, '');
  const groups = document.querySelectorAll('.episode-group');
  
  groups.forEach(g => {{
    const cards = g.querySelectorAll('.ref-card');
    let visible = 0;
    cards.forEach(c => {{
      const title = c.querySelector('.card-title').textContent.toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g, '');
      const author = c.querySelector('.card-author')?.textContent.toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g, '') || '';
      const cat = c.dataset.category;
      const match = (!q || title.includes(q) || author.includes(q));
      const catMatch = currentFilter === 'all' || cat === currentFilter;
      c.style.display = (match && catMatch) ? '' : 'none';
      if (match && catMatch) visible++;
    }});
    g.style.display = visible > 0 ? '' : 'none';
  }});
}}

function setFilter(cat) {{
  currentFilter = cat;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.toggle('active', b.textContent.includes(cat === 'all' ? 'Todas' : {{
    'cine': 'Cine', 'tv': 'TV', 'libros': 'Libros', 'comics': 'Cómics', 'musica': 'Música', 'videojuegos': 'Juegos'
  }}[cat])));
  filterRefs();
}}

function openModal(id) {{
  currentId = id;
  const r = catalog[id];
  if (!r) return;
  document.getElementById('modal').classList.add('open');
  document.body.style.overflow = 'hidden';
  renderModal(r);
}}

function renderModal(r) {{
  const cat = {{
    'cine': '🎬', 'tv': '📺', 'libros': '📚', 'comics': '📖', 'musica': '🎵', 'videojuegos': '🎮'
  }};
  const catNames = {{'cine':'Cine','tv':'TV','libros':'Libros','comics':'Cómics','musica':'Música','videojuegos':'Juegos'}};
  const coverHtml = r.cover ? `<div class="modal-cover"><img src="${{r.cover}}" alt="${{r.title}}"></div>` : '';
  const descHtml = r.description ? `<div class="modal-desc">${{r.description}}</div>` : '';
  const episodeHtml = r.episode ? `<div class="modal-episode">🎙️ ${{r.episode}}</div>` : '';
  const amazonHtml = r.amazon_url ? `<a class="modal-amazon" href="${{r.amazon_url}}" target="_blank" rel="noopener">📦 Comprar en Amazon</a>` : '';
  
  document.getElementById('modalBody').innerHTML = `
    ${{coverHtml}}
    <div class="modal-info">
      <div class="modal-title">${{r.title}}</div>
      ${{r.author ? `<div class="modal-author">${{r.author}}</div>` : ''}}
      <div class="modal-category">${{cat[r.category] || ''}} ${{catNames[r.category] || ''}}</div>
      ${{descHtml}}
      ${{episodeHtml}}
      ${{amazonHtml}}
    </div>
  `;
}}

function closeModal() {{
  document.getElementById('modal').classList.remove('open');
  document.body.style.overflow = '';
}}

function navModal(dir) {{
  let next = currentId + dir;
  while (next >= 0 && next < catalog.length) {{
    const r = catalog[next];
    const catMatch = currentFilter === 'all' || (r.category === currentFilter);
    const q = document.getElementById('search').value.toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g, '');
    const textMatch = !q || r.title.toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').includes(q) || (r.author||'').toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').includes(q);
    if (catMatch && textMatch) {{
      openModal(next);
      return;
    }}
    next += dir;
  }}
}}

document.addEventListener('keydown', e => {{
  if (e.key === 'Escape') closeModal();
  if (e.key === 'ArrowLeft') navModal(-1);
  if (e.key === 'ArrowRight') navModal(1);
}});
</script>
</body>
</html>'''

html = build_html()
with open(OUT, "w") as f:
    f.write(html)
print(f"HTML escrito: {OUT} ({os.path.getsize(OUT)//1024} KB)")
