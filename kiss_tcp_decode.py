#!/usr/bin/env python3
"""
Connects to soundmodem's KISS TCP server and decodes GEOSCAN/239Alferov
frames LIVE using the real SatsDecoder decoding classes (not a
reimplementation) — no SatsDecoder GUI needed.

IMPORTANT: this version forces a STABLE, non-timestamped output filename
per fnum (e.g. 239ALFEROV_N3.jpg), and reuses/appends to that same file
across SEPARATE runs of this script (different recordings, different
days) rather than starting a new timestamped file every time. This is
what actually lets chunks from multiple different recordings merge
into one complete image over time — SatsDecoder's own filename
generator stamps a fresh timestamp every run even with merge mode on,
which silently defeated cross-session merging until this fix.

Usage:
    python3 kiss_tcp_decode.py \
        --satsdecoder-path ~/alferov_pipeline/SatsDecoder \
        --host 127.0.0.1 --port 8100 \
        --outdir ./decoded_output

Run this WHILE play_recording.sh (or ocenaudio) is feeding audio into
soundmodem. It streams, decodes, and writes/validates output as data
arrives, and prints a live status line whenever a chunk is accepted.
"""
import argparse
import socket
import sys
import pathlib
import time

FEND, FESC, TFEND, TFESC = 0xC0, 0xDB, 0xDC, 0xDD


def log(msg):
    print(msg, flush=True)


class KissStreamParser:
    """Incremental KISS frame extractor for a live TCP stream (frames
    can arrive split across multiple socket reads)."""
    def __init__(self):
        self._buf = bytearray()
        self._in_frame = False

    def feed(self, chunk: bytes):
        frames = []
        for b in chunk:
            if b == FEND:
                if self._in_frame and self._buf:
                    frames.append(bytes(self._buf[1:]))  # drop cmd byte
                self._buf = bytearray()
                self._in_frame = True
            elif self._in_frame:
                self._buf.append(b)
        return frames


def patch_stable_filenames(protocol):
    """Force SatsDecoder's fid generator to produce a stable filename
    per (sat, fnum) with no timestamp, so re-running this script later
    against a DIFFERENT recording reuses (appends to) the same file on
    disk instead of starting a fresh one — true cross-session merging."""
    from SatsDecoder.systems.geoscan import get_sat_name
    ir = protocol.ir

    def stable_generate_fid(sat_num=None, t=None):
        pfx = get_sat_name(sat_num).rpartition('-')[0]
        hr = ir._last_is_hr and '_hr' or ''
        fnum = (ir._last_fnum > -1) and ('_N' + str(ir._last_fnum)) or ''
        fid = f'{pfx.upper()}{hr}{fnum}'
        ir.current_fid = fid
        return fid

    ir.generate_fid = stable_generate_fid
    ir.set_merge_mode(1)  # always merge within + across runs now


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--satsdecoder-path', required=True)
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, required=True)
    ap.add_argument('--outdir', required=True)
    args = ap.parse_args()

    sys.path.insert(0, args.satsdecoder_path)
    from SatsDecoder.systems.geoscan import GeoscanProtocol

    outdir = pathlib.Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    protocol = GeoscanProtocol(str(outdir))
    patch_stable_filenames(protocol)

    log(f"[+] connecting to {args.host}:{args.port} ...")
    sock = socket.create_connection((args.host, args.port), timeout=10)
    sock.settimeout(2.0)
    log("[+] connected. Waiting for frames (Ctrl+C to stop and finalize)...")
    log("[+] output filenames are now STABLE across runs (no timestamp) "
        "so separate recordings merge into the same file.")

    parser = KissStreamParser()
    n_events = 0
    last_status = time.time()

    try:
        while True:
            try:
                chunk = sock.recv(4096)
            except socket.timeout:
                if time.time() - last_status > 15:
                    log("    ... still listening, no data recently")
                    last_status = time.time()
                continue
            if not chunk:
                log("[+] connection closed by soundmodem.")
                break

            for frame in parser.feed(chunk):
                for kind, name, payload in protocol.recognize(frame):
                    if kind == 'img':
                        n_events += 1
                        x, img = payload
                        log(f"    [img] sat={name} fn={img.fn.name} "
                            f"packets={img.packets}")
    except KeyboardInterrupt:
        log("\n[+] stopping (Ctrl+C)...")
    finally:
        sock.close()
        for img in protocol.ir.images.values():
            img.flush()
            img.close()

    log(f"[+] {n_events} image event(s) processed")
    log(f"[+] checking output in {outdir} ...")
    try:
        from PIL import Image
    except ImportError:
        Image = None

    for f in sorted(outdir.iterdir()):
        size = f.stat().st_size
        status = ""
        if Image and f.suffix.lower() in ('.jpg', '.jpeg'):
            try:
                with Image.open(f) as im:
                    im.verify()
                status = " -> VALID image"
            except Exception:
                status = " -> not a valid/complete image yet"
        log(f"    {f.name} ({size} bytes){status}")


if __name__ == '__main__':
    main()
