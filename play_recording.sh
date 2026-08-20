#!/usr/bin/env bash
# Downloads (if given a URL) or plays (if given a local path) a
# recording into the virtual sink soundmodem is listening to — this
# replicates the forum tip of "download the file first, don't stream
# it live" without needing ocenaudio's GUI, though you can still open
# the file in ocenaudio manually and route it the same way if you
# prefer that workflow.
set -e

if [ -z "$1" ]; then
    echo "usage: $0 <local_audio_file_or_url>"
    exit 1
fi

WORKDIR="$HOME/alferov_pipeline"
INPUT="$1"

if [[ "$INPUT" == http* ]]; then
    FNAME="$WORKDIR/$(basename "$INPUT")"
    echo "[+] downloading $INPUT ..."
    wget -q -O "$FNAME" "$INPUT"
    INPUT="$FNAME"
fi

# Convert to a clean WAV first (handles mp3/ogg/whatever) so playback
# is consistent regardless of source format.
WAV="${INPUT%.*}_playback.wav"
if [ ! -f "$WAV" ]; then
    echo "[+] converting to WAV..."
    ffmpeg -y -loglevel error -i "$INPUT" -ar 48000 -ac 1 "$WAV"
fi

echo "[+] playing $WAV into the Alferov_Pipeline virtual sink..."
echo "    (make sure soundmodem's audio input is set to"
echo "     'Monitor of Alferov_Pipeline' before this finishes)"
paplay --device=alferov_pipe "$WAV"
echo "[+] playback finished."
