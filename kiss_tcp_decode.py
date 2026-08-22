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
import struct
import sys
import pathlib
import time

FEND, FESC, TFEND, TFESC = 0xC0, 0xDB, 0xDC, 0xDD


def is_plausible_frame(data: bytes) -> bool:
    """Reject frames whose fnum is absurd (256, 768, 1024, 1536, ...) —
    these are misdecoded noise, not real image chunks. The real
    satellite uses a small handful of image slots (observed: N0-N6ish),
    so anything outside a generous sane range is filtered before it
    ever reaches SatsDecoder and gets written to a garbage file."""
    if len(data) != 72 or data[0] != 0x09:
        return True  # not our concern here, let SatsDecoder's own logic handle it
    marker = struct.unpack_from('<I', data, 5)[0]
    if marker != 0x6F6B6F31:
        return True
    fnum = struct.unpack_from('<H', data, 13)[0]
    return fnum < 20


def log(msg):
    print(msg, flush=True)


class KissStreamParser:
    """Incremental KISS frame extractor for a live TCP stream (frames
    can arrive split across multiple socket reads).

    IMPORTANT: this now correctly un-escapes KISS framing. A literal
    0xDB byte in real data must be sent as 0xDB 0xDD (and a literal
    0xC0 as 0xDB 0xDC) so it isn't confused with the frame delimiter
    or escape byte. Since JPEG's DQT marker is literally 0xFF 0xDB,
    every DQT marker in the whole data stream was being escaped this
    way — and this parser previously never un-escaped it, corrupting
    every DQT segment (and any other literal 0xDB/0xC0 byte) in every
    file this pipeline has ever produced."""
    def __init__(self):
        self._buf = bytearray()
        self._in_frame = False
        self._escape = False

    def feed(self, chunk: bytes):
        frames = []
        for b in chunk:
            if b == FEND:
                if self._in_frame and self._buf:
                    frames.append(bytes(self._buf[1:]))  # drop cmd byte
                self._buf = bytearray()
                self._in_frame = True
                self._escape = False
            elif self._in_frame:
                if self._escape:
                    if b == TFEND:
                        self._buf.append(FEND)
                    elif b == TFESC:
                        self._buf.append(FESC)
                    else:
                        self._buf.append(b)  # malformed escape, pass through
                    self._escape = False
                elif b == FESC:
                    self._escape = True
                else:
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
    ap.add_argument('--heartbeat-interval', type=int, default=45,
                     help='seconds between "still listening" messages when '
                          'no data is arriving (default: 45; use a much '
                          'larger value like 900 for multi-day monitor.sh runs)')
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
    frame_counts = {}
    other_counts = {}
    last_status = time.time()

    try:
        while True:
            try:
                chunk = sock.recv(4096)
            except socket.timeout:
                if time.time() - last_status > args.heartbeat_interval:
                    now = time.strftime('%Y-%m-%d %H:%M:%S')
                    log(f"    ... [{now}] still listening, no data recently")
                    last_status = time.time()
                continue
            if not chunk:
                log("[+] connection closed by soundmodem.")
                break

            for frame in parser.feed(chunk):
                if not is_plausible_frame(frame):
                    continue
                for kind, name, payload in protocol.recognize(frame):
                    if kind == 'img':
                        n_events += 1
                        x, img = payload
                        fname = img.fn.name
                        prev_count = frame_counts.get(fname, 0)
                        frame_counts[fname] = prev_count + 1
                        # Only print on a NEW image number, or every
                        # 25th frame for one we've already seen —
                        # avoids one line per frame (can be hundreds).
                        if prev_count == 0 or frame_counts[fname] % 25 == 0:
                            log(f"    [img] fn={fname} "
                                f"({frame_counts[fname]} chunks so far)")
                    else:
                        # Housekeeping/telemetry and any other/unknown
                        # frame kind — previously silently ignored,
                        # which made telemetry-only reception windows
                        # look identical to "nothing happening at all".
                        # Same throttling approach: log on first sight
                        # of a kind, then every 25th after that.
                        n_events += 1
                        other_counts[kind] = other_counts.get(kind, 0) + 1
                        if other_counts[kind] == 1 or other_counts[kind] % 25 == 0:
                            log(f"    [{kind}] sat={name} "
                                f"({other_counts[kind]} frame(s) so far)")
    except KeyboardInterrupt:
        log("\n[+] stopping (Ctrl+C)...")
    finally:
        sock.close()
        for img in protocol.ir.images.values():
            img.flush()
            img.close()

    log(f"[+] {n_events} total frame event(s) processed")
    if frame_counts:
        log(f"    images: " + ", ".join(f"{k}={v}" for k, v in frame_counts.items()))
    if other_counts:
        log(f"    other:  " + ", ".join(f"{k}={v}" for k, v in other_counts.items()))
    if not frame_counts and not other_counts:
        log(f"    (nothing received this run)")
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
