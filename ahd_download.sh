#!/bin/bash
# Download episodes in small batches with delays
# This handles iVoox CDN rate limiting

AUDIO_DIR="$HOME/Boti/aqui-hay-dragones/audio"
mkdir -p "$AUDIO_DIR"

# Extract pending episodes - those not already downloaded
python3 -c "
import os, sys
audio_dir = os.path.expanduser('~/Boti/aqui-hay-dragones/audio')
with open('/tmp/ahd_episodes.txt') as f:
    lines = [l.strip() for l in f if l.strip()]
for line in lines:
    url, name, size_str = line.split('|')
    fpath = os.path.join(audio_dir, name + '.mp3')
    expected = int(size_str)
    if os.path.exists(fpath) and os.path.getsize(fpath) >= expected * 0.95:
        continue  # already have it
    print(url)
" > /tmp/ahd_pending.txt

total=$(wc -l < /tmp/ahd_pending.txt)
echo "Pending: $total episodes"

# Download in batches of 3
batch=0
while read -r url; do
    batch=$((batch + 1))
    
    # Extract filename from URL
    filename=$(echo "$url" | sed 's/.*\/\([^?]*\).*/\1/' | sed 's/.*\/\([^\/]*\)$/\1/' )
    
    echo "[$batch/$total] Downloading..."
    
    # Try with wget (more reliable for redirects)
    curl -L --max-time 300 -o "$AUDIO_DIR/temp.mp3" "$url" 2>/dev/null
    
    # Check if it's a real MP3
    if file "$AUDIO_DIR/temp.mp3" 2>/dev/null | grep -q "MPEG"; then
        # Rename using the safe name from our list
        safename=$(grep "$url" /tmp/ahd_episodes.txt | cut -d'|' -f2)
        mv "$AUDIO_DIR/temp.mp3" "$AUDIO_DIR/${safename}.mp3"
        size=$(stat -f%z "$AUDIO_DIR/${safename}.mp3" 2>/dev/null)
        echo "  ✓ ${safename}.mp3 ($(($size/1024/1024)) MB)"
    else
        echo "  ✗ Not an MP3 (got $(wc -c < "$AUDIO_DIR/temp.mp3") bytes)"
        rm -f "$AUDIO_DIR/temp.mp3"
    fi
    
    # Delay between downloads to avoid rate limiting
    if [ $((batch % 3)) -eq 0 ] && [ "$batch" -lt "$total" ]; then
        echo "  --- Batch pause (15s) ---"
        sleep 15
    else
        sleep 3
    fi
done < /tmp/ahd_pending.txt

echo ""
echo "Download complete!"
ls "$AUDIO_DIR"/*.mp3 | wc -l
du -sh "$AUDIO_DIR"
