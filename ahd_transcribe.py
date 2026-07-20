#!/opt/homebrew/Cellar/openai-whisper/20250625_3/libexec/bin/python3
"""
Aquí hay Dragones — Transcription Pipeline (CPU parallel)
Transcribes all MP3 episodes using Whisper on CPU with parallel workers.
Usage: python3 ahd_transcribe.py [--workers 7]
"""

import json, os, sys, time, re, subprocess, tempfile, argparse, threading
from pathlib import Path
from queue import Queue

BASE = Path.home() / "Boti" / "aqui-hay-dragones"
AUDIO_DIR = BASE / "audio"
TRANS_DIR = BASE / "transcripts"
PROGRESS_FILE = BASE / "transcribed.json"

TRANS_DIR.mkdir(exist_ok=True)
MODEL = "base"  # base is faster and works well for Spanish


def load_progress():
    if PROGRESS_FILE.exists():
        return set(json.loads(PROGRESS_FILE.read_text()))
    return set()


def save_progress(done):
    PROGRESS_FILE.write_text(json.dumps(sorted(done), indent=2))


def transcribe_one(mp3_path, srt_path, model):
    """Transcribe one episode, returns True on success."""
    try:
        # Convert to 16kHz mono WAV first
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            wav_path = f.name
        
        result = subprocess.run(
            ['ffmpeg', '-y', '-i', str(mp3_path), '-ar', '16000', '-ac', '1', wav_path],
            capture_output=True, timeout=300
        )
        if result.returncode != 0:
            print(f"  FFmpeg error: {result.stderr.decode()[:200]}")
            os.unlink(wav_path)
            return False
        
        # Transcribe on CPU
        result = model.transcribe(wav_path, language='es', task='transcribe', verbose=False)
        
        # Write SRT
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write(result['text'])
        
        os.unlink(wav_path)
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        try:
            os.unlink(wav_path)
        except:
            pass
        return False


def worker(worker_id, queue, model, progress_lock, done):
    """Worker thread that processes items from the queue."""
    while True:
        item = queue.get()
        if item is None:
            queue.task_done()
            break
        
        mp3, srt_path = item
        name = mp3.stem
        
        print(f"[W{worker_id}] {mp3.name}")
        ok = transcribe_one(mp3, srt_path, model)
        
        with progress_lock:
            if ok:
                done.add(name)
                save_progress(done)
                print(f"[W{worker_id}] ✓ {mp3.name}")
            else:
                print(f"[W{worker_id}] ✗ {mp3.name}")
        
        queue.task_done()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=7, help="Number of parallel workers")
    args = parser.parse_args()
    
    mp3s = sorted(AUDIO_DIR.glob("*.mp3"))
    print(f"Found {len(mp3s)} MP3 files")
    
    if not mp3s:
        print("No MP3 files found in audio/ directory.")
        sys.exit(1)
    
    done = load_progress()
    pending = [m for m in mp3s if m.stem not in done]
    print(f"Already transcribed: {len(done)}")
    print(f"Pending: {len(pending)}")
    
    if not pending:
        print("All done!")
        return
    
    # Create queue and add work items
    q = Queue()
    for mp3 in pending:
        srt_path = TRANS_DIR / f"{mp3.stem}.srt"
        q.put((mp3, srt_path))
    
    print(f"\nStarting {args.workers} CPU workers with model={MODEL}...")
    start = time.time()
    
    # Workers need their own model instance (Whisper isn't thread-safe for GPU)
    import whisper
    progress_lock = threading.Lock()
    
    threads = []
    for i in range(args.workers):
        print(f"  Loading model for worker {i+1}...")
        model = whisper.load_model(MODEL, device="cpu")
        t = threading.Thread(target=worker, args=(i+1, q, model, progress_lock, done))
        t.start()
        threads.append(t)
        time.sleep(2)  # Stagger model loading
    
    # Wait for all work to complete
    q.join()
    
    # Stop workers
    for _ in threads:
        q.put(None)
    for t in threads:
        t.join()
    
    elapsed = time.time() - start
    print(f"\n=== DONE ===")
    print(f"Transcribed {len(done)} episodes in {elapsed/60:.1f} minutes")
    print(f"Average: {elapsed/len(done)/60:.1f} min per episode")


if __name__ == "__main__":
    main()
