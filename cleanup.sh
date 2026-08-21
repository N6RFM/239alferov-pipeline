#!/usr/bin/env bash
# Tidies ~/alferov_pipeline: archives (doesn't delete) old logs, cached
# audio conversions, and superseded/garbage decoded_output files, while
# keeping every actual script and the current best output.
set -e

WORKDIR="${WORKDIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
cd "$WORKDIR"

ARCHIVE="$WORKDIR/_archive_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$ARCHIVE"

echo "[+] archiving old decoder logs..."
mkdir -p "$ARCHIVE/logs"
mv decoder_*.log "$ARCHIVE/logs/" 2>/dev/null || true

echo "[+] archiving cached WAV conversions (regenerated automatically as needed)..."
mkdir -p "$ARCHIVE/wav_cache"
mv *_playback.wav "$ARCHIVE/wav_cache/" 2>/dev/null || true

echo "[+] archiving known-garbage decoded output (N768/N1024 noise artifacts)..."
mkdir -p "$ARCHIVE/decoded_output_garbage"
mv decoded_output/*N768*.jpg decoded_output/*N1024*.jpg "$ARCHIVE/decoded_output_garbage/" 2>/dev/null || true

echo "[+] archiving superseded timestamped N3 fragments (now replaced by stable 239ALFEROV_N3.jpg)..."
mkdir -p "$ARCHIVE/decoded_output_old_fragments"
find decoded_output -maxdepth 1 -name '239ALFEROV_N3_*.jpg' -exec mv {} "$ARCHIVE/decoded_output_old_fragments/" \; 2>/dev/null || true

echo "[+] archiving intermediate repair/preview attempts (keeping the final one)..."
mkdir -p "$ARCHIVE/repair_attempts"
for f in decoded_output/N3_repaired.jpg decoded_output/N3_repaired.png \
         decoded_output/N3_partial_preview.png decoded_output/N3_imagemagick_preview.png \
         decoded_output/N3_ffmpeg_preview.png; do
    [ -f "$f" ] && mv "$f" "$ARCHIVE/repair_attempts/"
done

echo ""
echo "===================================================================="
echo "KEPT (still in place, untouched):"
echo "  - All scripts: go.sh, play_recording.sh, kiss_tcp_decode.py,"
echo "    setup.sh, repair_jpeg.py, splice_donor_header.py, find_gaps.py"
echo "  - donor_N3_header_source.jpg (reference file, still useful)"
echo "  - decoded_output/239ALFEROV_N3.jpg (current best merged output)"
echo "  - decoded_output/N3_final_attempt.jpg (latest spliced attempt)"
echo "  - soundmodem/, wine/, SatsDecoder/ (required infrastructure)"
echo "  - Original recordings (.mp3/.ogg — not touched, they're your source data)"
echo ""
echo "ARCHIVED to: $ARCHIVE"
echo "  (nothing was deleted — remove that folder yourself once you're"
echo "   sure you don't need any of it)"
echo "===================================================================="

echo ""
echo "[+] current top-level contents:"
ls -la "$WORKDIR"
