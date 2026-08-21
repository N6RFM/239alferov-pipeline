#!/usr/bin/env bash
# Normal use: just run this with a recording. If soundmodem is already
# running from a previous call, it's reused silently — no window, no
# prompt, nothing to look at. Only pass --reset if something's actually
# broken (stuck process, port conflict) and you need a clean restart.
set -e

WORKDIR="${WORKDIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"

# Defensive: browser-downloaded files often lose the executable bit.
chmod +x "$WORKDIR"/*.sh 2>/dev/null || true
KISS_PORT="${KISS_PORT:-8100}"
OUTDIR="${OUTDIR:-$WORKDIR/decoded_output}"
RESET=0

ARGS=()
for a in "$@"; do
    if [ "$a" = "--reset" ]; then RESET=1; else ARGS+=("$a"); fi
done

if [ -z "${ARGS[0]}" ]; then
    echo "usage: $0 [--reset] <recording_file>"
    exit 1
fi
RECORDING="${ARGS[0]}"

# Preflight: sanity-check the recording before spending time decoding
# it — catches truncated downloads / corrupt files early instead of
# discovering it after a full run.
if command -v ffprobe >/dev/null 2>&1; then
    PREFLIGHT="$(ffprobe -v error -show_entries format=duration,size \
        -of default=noprint_wrappers=1 "$RECORDING" 2>&1)"
    if [ $? -ne 0 ]; then
        echo "[!] WARNING: ffprobe couldn't read '$RECORDING' — it may be"
        echo "    corrupt or an incomplete download. Proceeding anyway,"
        echo "    but expect a failed/empty decode if this is the case."
    else
        DURATION=$(echo "$PREFLIGHT" | grep duration= | cut -d= -f2 | cut -d. -f1)
        echo "[+] preflight: $RECORDING is ${DURATION:-?}s long"
        if [ -n "$DURATION" ] && [ "$DURATION" -lt 30 ] 2>/dev/null; then
            echo "[!] WARNING: recording is under 30 seconds — this may be"
            echo "    a truncated/incomplete download rather than a full pass."
        fi
    fi
fi
cd "$WORKDIR"
mkdir -p "$OUTDIR"

pkill -9 -f kiss_tcp_decode.py 2>/dev/null || true

SOUNDMODEM_RUNNING=0
pgrep -f hs_soundmodem.exe >/dev/null 2>&1 && SOUNDMODEM_RUNNING=1

if [ "$RESET" = "1" ] || [ "$SOUNDMODEM_RUNNING" = "0" ]; then
    echo "[+] (re)starting soundmodem from a clean state..."
    sudo fuser -k "${KISS_PORT}/tcp" 2>/dev/null || true
    WINEPREFIX="$WORKDIR/wine" wineserver -k 2>/dev/null || true
    sleep 2

    env WINEARCH=win32 WINEPREFIX="$WORKDIR/wine" \
        wine "$WORKDIR/soundmodem/hs_soundmodem.exe" &
    sleep 3

    echo ""
    echo "===================================================================="
    echo "SET THESE 3 THINGS, then click OK (only needed after a reset):"
    echo "   1. Protocol:      GEOSCAN 2.7 9600bd"
    echo "   2. Input device:  Monitor of Alferov_Pipeline"
    echo "   3. KISS Server:   port $KISS_PORT, box CHECKED"
    echo ""
    echo "(soundmodem has no frequency setting — it only processes audio,"
    echo "it never tunes anything. That's handled upstream, wherever the"
    echo "recording/audio actually came from.)"
    echo ""
    echo "TIP: tick 'Minimized window on startup' in the same dialog so it"
    echo "stops popping up in front every time you reset."
    echo "===================================================================="
    read -p "Press Enter once all 3 are set and you clicked OK... "
else
    echo "[+] soundmodem already running — reusing it, no window needed."
fi

DECODER_LOG="$WORKDIR/decoder_$(date +%s).log"
echo "[+] starting decoder..."
python3 -u "$WORKDIR/kiss_tcp_decode.py" \
    --satsdecoder-path "$WORKDIR/SatsDecoder" \
    --host 127.0.0.1 --port "$KISS_PORT" \
    --outdir "$OUTDIR" \
    > "$DECODER_LOG" 2>&1 &
DECODER_PID=$!
sleep 2

if ! kill -0 "$DECODER_PID" 2>/dev/null; then
    echo "[!] decoder failed to start — likely soundmodem's KISS server"
    echo "    isn't actually enabled/reachable. Try: $0 --reset \"$RECORDING\""
    cat "$DECODER_LOG"
    exit 1
fi

echo "[+] playing recording (this takes as long as the recording itself)..."
"$WORKDIR/play_recording.sh" "$RECORDING"

echo "[+] playback done, stopping decoder..."
sleep 2
kill -INT "$DECODER_PID" 2>/dev/null || true
for i in $(seq 1 10); do
    kill -0 "$DECODER_PID" 2>/dev/null || break
    sleep 1
done
kill -9 "$DECODER_PID" 2>/dev/null || true
wait "$DECODER_PID" 2>/dev/null || true

echo ""
echo "===================================================================="
echo "RESULTS (this run only):"
echo "===================================================================="
cat "$DECODER_LOG"

echo ""
echo "===================================================================="
echo "OUTPUT FILE CHECK (checked directly, not from the decoder's own log,"
echo "since the decoder's shutdown summary is unreliable):"
echo "===================================================================="
python3 "$WORKDIR/alferov_lib.py" "$OUTDIR"/*.jpg 2>/dev/null || echo "  (no output files yet)"
