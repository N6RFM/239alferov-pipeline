#!/usr/bin/env bash
# Quick status check of everything in decoded_output/ — no decoding,
# just reports what's there right now.
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="${WORKDIR:-$SCRIPT_DIR}"
OUTDIR="${OUTDIR:-$WORKDIR/decoded_output}"

if [ ! -d "$OUTDIR" ] || [ -z "$(ls -A "$OUTDIR"/*.jpg 2>/dev/null)" ]; then
    echo "No decoded images yet in $OUTDIR"
    exit 0
fi

echo "Status of $OUTDIR:"
echo ""
python3 "$SCRIPT_DIR/alferov_lib.py" "$OUTDIR"/*.jpg
