#!/opt/homebrew/Cellar/openai-whisper/20250625_3/libexec/bin/python3
"""
Aquí hay Dragones — Transcription Pipeline
Transcribes all MP3 episodes using Whisper with MPS acceleration.
Usage: python3 ahd_transcribe.py
"""

import json, os, sys, time, re, subprocess, tempfile
from pathlib import Path

BASE = Path.home() / "Boti" / "aqui-hay-dragones"
AUDIO_DIR = BASE / "audio"
TRANS_DIR = BASE / "transcripts"
PROGRESS_FILE = BASE / "transcribed.json"

TRANS_DIR.mkdir(exist_ok=True)

# Model selection: base is good for Spanish (faster than small, better than tiny)
MODEL = "small"

def get_episode_title_from_filename(filename):
    """Extract a clean episode title from the MP3 filename."""
    name = filename.replace(".mp3", "")
    # Remove the AHD prefix stuff
    name = re.sub(r'^AHD\s*', '', name)
    name = name.replace('_', ' ')
    # Clean up
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def load_progress():
    if PROGRESS_FILE.exists():
        return set(json.loads(PROGRESS_FILE.read_text()))
    return set()

def save_progress(done):
    PROGRESS_FILE.write_text(json.dumps(sorted(done), indent=2))

def transcribe_one(mp3_path, srt_path, model):
    """Transcribe one episode, returns True on success."""
    print(f"  Transcribing {mp3_path.name}...")
    
    # Convert to 16kHz mono WAV first (Whisper works better)
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        wav_path = f.name
    
    try:
        result = subprocess.run(
            ['ffmpeg', '-y', '-i', str(mp3_path), '-ar', '16000', '-ac', '1', wav_path],
            capture_output=True, timeout=300
        )
        if result.returncode != 0:
            print(f"  FFmpeg error: {result.stderr.decode()[:200]}")
            return False
        
        # Transcribe
        result = model.transcribe(wav_path, language='es', task='transcribe', verbose=False)
        
        # Write SRT
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write(result['text'])
        
        print(f"  ✓ {len(result['text'])} chars")
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False
    finally:
        if os.path.exists(wav_path):
            os.unlink(wav_path)

def main():
    import whisper
    
    # Find all downloaded MP3s
    mp3s = sorted(AUDIO_DIR.glob("*.mp3"))
    print(f"Found {len(mp3s)} MP3 files")
    
    if not mp3s:
        print("No MP3 files found in audio/ directory.")
        print("Make sure downloads are complete first.")
        sys.exit(1)
    
    # Load progress
    done = load_progress()
    pending = [m for m in mp3s if m.stem not in done]
    print(f"Already transcribed: {len(done)}")
    print(f"Pending: {len(pending)}")
    
    if not pending:
        print("All done!")
        return
    
    # Load model
    device = "mps"
    print(f"Loading Whisper {MODEL} model on {device}...")
    model = whisper.load_model(MODEL, device=device)
    print("Model loaded.")
    
    # Transcribe one by one
    start = time.time()
    for i, mp3 in enumerate(pending):
        srt_path = TRANS_DIR / f"{mp3.stem}.srt"
        print(f"\n[{i+1}/{len(pending)}] {mp3.name}")
        
        ok = transcribe_one(mp3, srt_path, model)
        if ok:
            done.add(mp3.stem)
            save_progress(done)
        
        elapsed = time.time() - start
        rate = (i+1) / elapsed * 3600 if elapsed > 0 else 0
        remaining = len(pending) - i - 1
        eta = remaining / rate if rate > 0 else 0
        print(f"  Rate: {rate:.1f} ep/hr | ETA: {eta:.1f}h")
    
    elapsed_total = time.time() - start
    print(f"\n=== DONE ===")
    print(f"Transcribed {len(done)} episodes in {elapsed_total/60:.1f} minutes")
    print(f"Average: {elapsed_total/len(done)/60:.1f} min per episode")

if __name__ == "__main__":
    main()
