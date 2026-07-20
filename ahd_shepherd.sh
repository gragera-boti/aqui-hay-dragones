# Shepherd script for Aquí hay Dragones transcription
# Runs Whisper on MPS with tiny model, one episode at a time
# Usage: bash ahd_shepherd.sh

WHISPER_PY="/opt/homebrew/Cellar/openai-whisper/20250625_3/libexec/bin/python3"
BASE="$HOME/Boti/aqui-hay-dragones"
AUDIO_DIR="$BASE/audio"
TRANS_DIR="$BASE/transcripts"
PROGRESS_FILE="$BASE/transcribed.json"
mkdir -p "$TRANS_DIR"

# Find pending episodes
echo "Checking pending episodes..."
PENDING=$($WHISPER_PY -c "
import json, os
from pathlib import Path
progress = set()
if os.path.exists('$PROGRESS_FILE'):
    progress = set(json.loads(open('$PROGRESS_FILE').read()))
audio_dir = Path('$AUDIO_DIR')
all_mp3s = sorted(audio_dir.glob('*.mp3'))
pending = [m for m in all_mp3s if m.stem not in progress]
print(len(pending))
for m in pending:
    print(m.name)
")

read TOTAL <<< "$PENDING"
echo "Total: $TOTAL pending episodes"

# Process one at a time on MPS
COUNT=0
START_TIME=$(date +%s)

$WHISPER_PY -c "
import json, os, sys, time, subprocess, tempfile, whisper
from pathlib import Path

AUDIO_DIR = Path('$AUDIO_DIR')
TRANS_DIR = Path('$TRANS_DIR')
PROGRESS_FILE = '$PROGRESS_FILE'
MODEL_NAME = 'tiny'

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        return set(json.loads(open(PROGRESS_FILE).read()))
    return set()

def save_progress(done):
    open(PROGRESS_FILE, 'w').write(json.dumps(sorted(done), indent=2))

done = load_progress()
all_mp3s = sorted(AUDIO_DIR.glob('*.mp3'))
pending = [m for m in all_mp3s if m.stem not in done]

print(f'Loading Whisper {MODEL_NAME} on MPS...')
model = whisper.load_model(MODEL_NAME, device='mps')
print(f'Ready. Processing {len(pending)} episodes...')
sys.stdout.flush()

t0 = time.time()
for i, mp3 in enumerate(pending):
    ep_start = time.time()
    srt_path = TRANS_DIR / f'{mp3.stem}.srt'
    name = mp3.stem.replace('_', ' ')[:60]
    
    print(f'[{i+1}/{len(pending)}] {name}...')
    sys.stdout.flush()
    
    # Convert to WAV
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        wav_path = f.name
    subprocess.run(['ffmpeg', '-y', '-i', str(mp3), '-ar', '16000', '-ac', '1', wav_path], 
                   capture_output=True, timeout=300)
    
    # Transcribe
    result = model.transcribe(wav_path, language='es', task='transcribe', verbose=False)
    open(srt_path, 'w', encoding='utf-8').write(result['text'])
    os.unlink(wav_path)
    
    # Save progress
    done.add(mp3.stem)
    save_progress(done)
    
    ep_time = time.time() - ep_start
    total_elapsed = time.time() - t0
    rate = (i+1) / total_elapsed * 3600
    remaining = len(pending) - i - 1
    eta = remaining / rate if rate > 0 else 0
    
    print(f'  ✓ {ep_time:.0f}s | Rate: {rate:.1f} ep/h | ETA: {eta:.1f}h | Total: {len(done)}/{len(all_mp3s)}')
    sys.stdout.flush()

total_time = time.time() - t0
print(f'\\n=== DONE ===')
print(f'Transcribed {len(done)} episodes in {total_time/60:.1f} min')
print(f'Average: {total_time/len(done)/60:.1f} min per episode')
sys.stdout.flush()
"
