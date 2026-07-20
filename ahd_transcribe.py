#!/opt/homebrew/Cellar/openai-whisper/20250625_3/libexec/bin/python3
"""
Aquí hay Dragones — Transcription (MPS tiny)
Transcribes MP3 episodes using Whisper tiny on MPS, one at a time.
Usage: python3 ahd_transcribe.py
"""

import json, os, sys, time, subprocess, tempfile
from pathlib import Path

BASE = Path.home() / "Boti" / "aqui-hay-dragones"
AUDIO_DIR = BASE / "audio"
TRANS_DIR = BASE / "transcripts"
PROGRESS_FILE = BASE / "transcribed.json"
TRANS_DIR.mkdir(exist_ok=True)

MODEL = "tiny"
DEVICE = "mps"


def load_progress():
    if PROGRESS_FILE.exists():
        return set(json.loads(PROGRESS_FILE.read_text()))
    return set()


def save_progress(done):
    PROGRESS_FILE.write_text(json.dumps(sorted(done), indent=2))


def main():
    import whisper
    
    mp3s = sorted(AUDIO_DIR.glob("*.mp3"))
    print(f"Found {len(mp3s)} MP3 files")
    
    if not mp3s:
        print("No MP3 files found.")
        sys.exit(1)
    
    done = load_progress()
    pending = [m for m in mp3s if m.stem not in done]
    print(f"Already transcribed: {len(done)}")
    print(f"Pending: {len(pending)}")
    
    if not pending:
        print("All done!")
        return
    
    print(f"Loading Whisper {MODEL} on {DEVICE}...")
    model = whisper.load_model(MODEL, device=DEVICE)
    print(f"Ready. Processing {len(pending)} episodes...")
    sys.stdout.flush()
    
    t0 = time.time()
    for i, mp3 in enumerate(pending):
        ep_start = time.time()
        srt_path = TRANS_DIR / f"{mp3.stem}.srt"
        
        print(f"\n[{i+1}/{len(pending)}] {mp3.name}")
        sys.stdout.flush()
        
        # Convert to WAV
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            wav_path = f.name
        subprocess.run(
            ['ffmpeg', '-y', '-i', str(mp3), '-ar', '16000', '-ac', '1', wav_path],
            capture_output=True, timeout=300
        )
        
        # Transcribe
        result = model.transcribe(wav_path, language='es', task='transcribe', verbose=False)
        
        # Save SRT
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write(result['text'])
        
        os.unlink(wav_path)
        
        # Progress
        done.add(mp3.stem)
        save_progress(done)
        
        ep_time = time.time() - ep_start
        total_elapsed = time.time() - t0
        rate = (i + 1) / total_elapsed * 3600
        remaining = len(pending) - i - 1
        eta = remaining / rate if rate > 0 else 0
        
        print(f"  ✓ {ep_time:.0f}s | Rate: {rate:.1f} ep/h | ETA: {eta:.1f}h")
        sys.stdout.flush()
    
    total = time.time() - t0
    print(f"\n=== DONE ===")
    print(f"Transcribed {len(done)} episodes in {total/60:.1f} min")
    print(f"Average: {total/len(done)/60:.1f} min per episode")


if __name__ == "__main__":
    main()
