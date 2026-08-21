#!/usr/bin/env bash
# Pick one or more recordings and run them through go.sh sequentially.
#
# Usage:
#   ./batch.sh                          # interactive picker
#   ./batch.sh file1.ogg file2.ogg      # run these specific files, in order
#   ./batch.sh *.ogg                    # shell-expanded glob works too
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Defensive: browser-downloaded files often lose the executable bit.
# Fix it every time rather than relying on remembering chmod manually.
chmod +x "$SCRIPT_DIR"/*.sh 2>/dev/null || true
WORKDIR="${WORKDIR:-$SCRIPT_DIR}"

FILES=()

if [ "$#" -gt 0 ]; then
    FILES=("$@")
else
    # Interactive picker: list every recording found, let the user pick
    # one, several (space-separated numbers), or all.
    mapfile -t CANDIDATES < <(find "$WORKDIR" -maxdepth 1 -type f \
        \( -iname '*.ogg' -o -iname '*.mp3' -o -iname '*.wav' \) \
        ! -iname '*_playback.wav' -printf '%f\n' | sort)

    if [ "${#CANDIDATES[@]}" -eq 0 ]; then
        echo "[!] no .ogg/.mp3/.wav recordings found in $WORKDIR"
        exit 1
    fi

    echo "Recordings found in $WORKDIR:"
    for i in "${!CANDIDATES[@]}"; do
        printf "  %2d) %s\n" "$((i+1))" "${CANDIDATES[$i]}"
    done
    echo ""
    echo "Enter numbers to run (e.g. '1 3 4'), a range (e.g. '1-3'),"
    echo "'all' for everything, or Ctrl+C to cancel."
    read -p "> " SELECTION

    if [ "$SELECTION" = "all" ]; then
        FILES=("${CANDIDATES[@]}")
    else
        # expand ranges like "1-3" into "1 2 3", then collect by index
        EXPANDED=()
        for tok in $SELECTION; do
            if [[ "$tok" =~ ^([0-9]+)-([0-9]+)$ ]]; then
                for ((n=${BASH_REMATCH[1]}; n<=${BASH_REMATCH[2]}; n++)); do
                    EXPANDED+=("$n")
                done
            else
                EXPANDED+=("$tok")
            fi
        done
        for n in "${EXPANDED[@]}"; do
            idx=$((n-1))
            if [ "$idx" -ge 0 ] && [ "$idx" -lt "${#CANDIDATES[@]}" ]; then
                FILES+=("${CANDIDATES[$idx]}")
            else
                echo "[!] skipping invalid selection: $n"
            fi
        done
    fi

    if [ "${#FILES[@]}" -eq 0 ]; then
        echo "[!] nothing selected, exiting."
        exit 1
    fi
fi

echo ""
echo "===================================================================="
echo "Will run ${#FILES[@]} file(s), in this order:"
for f in "${FILES[@]}"; do echo "  - $f"; done
echo "===================================================================="
echo ""

FIRST=1
for f in "${FILES[@]}"; do
    echo ""
    echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
    echo ">>> $f"
    echo ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
    if [ "$FIRST" = "1" ]; then
        "$SCRIPT_DIR/go.sh" "$f"
        FIRST=0
    else
        "$SCRIPT_DIR/go.sh" "$f"
    fi
done

echo ""
echo "===================================================================="
echo "ALL RUNS COMPLETE — combined status of everything in decoded_output/:"
echo "===================================================================="
python3 -c "
from PIL import Image
import pathlib
outdir = pathlib.Path('$WORKDIR/decoded_output')
for f in sorted(outdir.glob('*.jpg')):
    size = f.stat().st_size
    try:
        Image.open(f).verify()
        print(f'  {f.name} ({size} bytes) -> VALID')
    except Exception as e:
        print(f'  {f.name} ({size} bytes) -> not valid/complete ({e})')
"
