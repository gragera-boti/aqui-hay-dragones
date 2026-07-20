#!/usr/bin/env python3
"""Generate a live status page for Aquí hay Dragones transcription progress."""
import json, os
from pathlib import Path

BASE = Path.home() / "Boti" / "aqui-hay-dragones"
INDEX = BASE / "index.html"
TRANS = BASE / "transcripts"
PROGRESS = BASE / "transcribed.json"
REFS = BASE / "REFERENCIAS_COMPLETAS.json"

# Gather stats
total_episodes = 138
transcribed = set()
if PROGRESS.exists():
    transcribed = set(json.loads(PROGRESS.read_text()))

total_size = sum(f.stat().st_size for f in sorted(TRANS.glob("*.srt")))
total_size_mb = total_size / 1024 / 1024

# Check extraction progress
extracted_eps = set()
if REFS.exists():
    data = json.loads(REFS.read_text())
    for ep in data.get("episodes", []):
        extracted_eps.add(ep["episode"])
    total_refs = data.get("total_references", 0)
else:
    total_refs = 0

# Build episode list
episodes = []
for srt_path in sorted(TRANS.glob("*.srt")):
    name = srt_path.stem.replace("_", " ")
    name = name.replace("AHD ", "AHD")
    epsize = srt_path.stat().st_size
    status = "✅" if name in extracted_eps else "📝"
    episodes.append((name, epsize, status))

# Sort by episode number (AHD2, AHD4, ... AHD276)
def sort_key(name):
    import re
    m = re.search(r'AHD(\d+)', name)
    return int(m.group(1)) if m else 0

episodes.sort(key=lambda x: sort_key(x[0]))

html = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<title>🐉 Aquí hay Dragones · Progreso</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Marcellus&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#0a0806;--surface:#14110e;--card:#1a1612;--border:#2a241f;--gold:#c9903a;--gold-light:#e8b45a;--gold-dim:rgba(201,144,58,.08);--text:#f0ede8;--text-dim:#9e948a;--text-muted:#6b6258;--radius:12px;--radius-sm:8px;--font:'Inter',sans-serif;--font-display:'Marcellus','Inter',serif}
body{font-family:var(--font);background:var(--bg);color:var(--text);line-height:1.6;min-height:100vh}
::selection{background:var(--gold);color:#000}

.header{text-align:center;padding:48px 24px 36px;border-bottom:1px solid var(--border);background:radial-gradient(ellipse 80% 60% at 50% 0%,rgba(201,144,58,.08) 0%,transparent 70%),var(--bg)}
.header h1{font-family:var(--font-display);font-size:clamp(1.5rem,5vw,2.8rem);font-weight:400;color:var(--text)}
.header h1 span{color:var(--gold-light)}
.header p{color:var(--text-dim);font-size:14px;margin-top:8px}

.stats{display:flex;flex-wrap:wrap;justify-content:center;gap:10px;margin-top:24px}
.stat{padding:12px 20px;border-radius:var(--radius-sm);background:var(--surface);border:1px solid var(--border);text-align:center;min-width:100px}
.stat .num{font-size:24px;font-weight:700;color:var(--gold-light)}
.stat .label{font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;margin-top:2px}

.progress-bar-wrap{max-width:500px;margin:16px auto 0;background:var(--surface);border-radius:8px;overflow:hidden;height:8px;border:1px solid var(--border)}
.progress-bar{height:100%;background:linear-gradient(90deg,var(--gold),var(--gold-light));transition:width 2s ease;border-radius:6px}

.container{max-width:900px;margin:0 auto;padding:24px}

.ep-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:6px}
.ep-item{display:flex;align-items:center;gap:10px;padding:10px 14px;border-radius:var(--radius-sm);background:var(--surface);border:1px solid var(--border);font-size:13px}
.ep-item .status{font-size:16px;flex-shrink:0}
.ep-item .name{flex:1;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ep-item .size{color:var(--text-muted);font-size:11px;white-space:nowrap}
.ep-item.pending{opacity:.4}
.ep-item.pending .status{opacity:.3}

.footer{text-align:center;padding:32px 24px;border-top:1px solid var(--border);color:var(--text-muted);font-size:13px}
.footer a{color:var(--gold);text-decoration:none}

@media(max-width:600px){
  .header{padding:32px 16px 24px}
  .ep-grid{grid-template-columns:1fr}
  .container{padding:16px}
}
</style>
</head>
<body>
<header class="header">
  <h1>🐉 Aquí hay Dragones · <span>Progreso</span></h1>
  <p>Transcripción y extracción de referencias culturales de 138 episodios</p>
  <div class="stats">
    <div class="stat"><div class="num">""" + str(len(transcribed)) + """</div><div class="label">Transcritos</div></div>
    <div class="stat"><div class="num">""" + str(total_episodes) + """</div><div class="label">Total</div></div>
    <div class="stat"><div class="num">""" + f"{total_size_mb:.0f}" + """</div><div class="label">MB de texto</div></div>
    <div class="stat"><div class="num">""" + str(len(extracted_eps)) + """</div><div class="label">Extraídos</div></div>
  </div>
  <div class="progress-bar-wrap">
    <div class="progress-bar" style="width:""" + f"{len(transcribed)/total_episodes*100:.1f}" + """%"></div>
  </div>
</header>
<div class="container">
  <div class="ep-grid">
"""

for name, size, status in episodes:
    cls = "" if status == "✅" else "pending"
    size_str = f"{size/1024:.0f} KB" if size < 1024*1024 else f"{size/1024/1024:.1f} MB"
    html += f'    <div class="ep-item {cls}"><span class="status">{status}</span><span class="name">{name}</span><span class="size">{size_str}</span></div>\n'

html += """  </div>
</div>
<footer class="footer">
  <p>Generado el """ + __import__('datetime').datetime.now().strftime("%d/%m/%Y %H:%M") + """ · <a href="https://github.com/gragera-boti/aqui-hay-dragones">GitHub</a></p>
</footer>
</body>
</html>"""

INDEX.write_text(html)
print(f"Status page generated: {len(transcribed)}/{total_episodes} transcribed, {total_size_mb:.0f} MB text")
print(f"Extracted: {len(extracted_eps)} episodes, {total_refs} references")
