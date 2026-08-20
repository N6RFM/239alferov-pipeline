#!/usr/bin/env bash
# 239Alferov soundmodem + SatsDecoder pipeline setup.
# Automates every download/install step. soundmodem's own protocol
# config (baud/freq/KISS-server-enable) is a one-time manual GUI step
# in a closed third-party Windows app — that part can't be reliably
# scripted, so this prints clear instructions for it instead of faking
# automation that would silently break on a UI change.
set -e

WORKDIR="${WORKDIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
mkdir -p "$WORKDIR"
cd "$WORKDIR"

echo "[1/6] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y wine unzip wget git python3-pip python3-tk pulseaudio-utils ffmpeg

echo "[2/6] Downloading soundmodem (geoscan27)..."
if [ ! -d soundmodem ]; then
    wget -q -O geoscan27.zip http://uz7.ho.ua/geoscan27.zip || \
    wget -q -O geoscan27.zip http://r4uab.ru/program/modem/geoscan27.zip
    unzip -q -o geoscan27.zip -d soundmodem
fi

echo "[3/6] Setting up Wine prefix..."
export WINEARCH=win32
export WINEPREFIX="$WORKDIR/wine"
if [ ! -d "$WINEPREFIX" ]; then
    wineboot --init 2>/dev/null
fi

echo "[4/6] Downloading + installing ocenaudio (optional — skipped on failure)..."
if ! command -v ocenaudio >/dev/null 2>&1; then
    UBUNTU_VER=$(lsb_release -rs 2>/dev/null || echo "24.04")
    if wget -q -O ocenaudio.deb --user-agent="Mozilla/5.0" \
        "https://www.ocenaudio.com/start_download/ocenaudio_ubuntu${UBUNTU_VER}.deb" \
        && file ocenaudio.deb | grep -qi debian; then
        sudo apt-get install -y ./ocenaudio.deb || \
            echo "[!] ocenaudio install failed — continuing without it (play_recording.sh doesn't need it)."
    else
        echo "[!] ocenaudio download didn't return a valid .deb — continuing without it."
        echo "    You can install it manually later from https://www.ocenaudio.com/download"
        echo "    play_recording.sh works fine without it in the meantime."
        rm -f ocenaudio.deb
    fi
fi

echo "[5/6] Cloning SatsDecoder (used headlessly, no GUI needed)..."
if [ ! -d SatsDecoder ]; then
    git clone --depth 1 https://github.com/baskiton/SatsDecoder.git
fi
pip install construct Pillow "numpy<2" --break-system-packages -q

echo "[6/6] Creating a virtual audio sink for routing recordings into soundmodem..."
if ! pactl list short sinks | grep -q alferov_pipe; then
    pactl load-module module-null-sink sink_name=alferov_pipe sink_properties=device.description=Alferov_Pipeline >/dev/null
fi

echo ""
echo "===================================================================="
echo "Setup complete. ONE-TIME MANUAL STEP required (soundmodem is a"
echo "closed third-party GUI app under Wine — this can't be scripted):"
echo ""
echo "  1. Launch soundmodem:"
echo "       env WINEARCH=win32 WINEPREFIX=\"$WORKDIR/wine\" wine \"$WORKDIR/soundmodem/hs_soundmodem.exe\""
echo "  2. In Settings: select the GEOSCAN protocol, 9600 baud,"
echo "     436.270 MHz center frequency."
echo "  3. Set the audio INPUT device to: 'Monitor of Alferov_Pipeline'"
echo "     (this is the virtual sink this script just created)."
echo "  4. Enable the KISS server (not just AGWPE) on a port, e.g. 8100."
echo "  5. Leave it running."
echo ""
echo "Once that's done, use play_recording.sh to feed it a downloaded"
echo "recording, and kiss_tcp_decode.py to decode headlessly (no"
echo "SatsDecoder GUI needed)."
echo "===================================================================="
