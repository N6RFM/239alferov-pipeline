#!/usr/bin/env bash
# Continuous live monitoring: connects to soundmodem's KISS server and
# just stays connected, writing chunks to disk as they arrive, for as
# long as this keeps running. No file, no timeout, no auto-stop —
# unlike go.sh/batch.sh, which are for finite recorded files.
#
# Pair this with the live-audio GRC flowgraph (continuous Airspy ->
# FM demod -> Audio Sink -> Alferov_Pipeline), not with play_recording.sh.
#
# Stop with Ctrl+C when you're done.
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="${WORKDIR:-$SCRIPT_DIR}"
KISS_PORT="${KISS_PORT:-8100}"
OUTDIR="${OUTDIR:-$WORKDIR/decoded_output}"

chmod +x "$WORKDIR"/*.sh 2>/dev/null || true
mkdir -p "$OUTDIR"

echo "[+] starting continuous live monitoring..."
echo "[+] make sure soundmodem is already running and configured"
echo "    (KISS server enabled on port $KISS_PORT), and your live-audio"
echo "    GRC flowgraph is running and feeding it."
echo "[+] output: $OUTDIR"
echo "[+] press Ctrl+C to stop"
echo ""

python3 -u "$WORKDIR/kiss_tcp_decode.py" \
    --satsdecoder-path "$WORKDIR/SatsDecoder" \
    --host 127.0.0.1 --port "$KISS_PORT" \
    --outdir "$OUTDIR"
