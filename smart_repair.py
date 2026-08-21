#!/usr/bin/env python3
"""
Combined, sequential-only JPEG repair: walks markers strictly in order
from SOI (never scans blindly for byte patterns, which causes false
positives). When a segment's declared length is implausible:

  - If it overlaps a KNOWN gap (from find_gaps.py's zero-run detection):
    this is genuinely missing data. Skip the segment and search forward
    for the next real marker to resynchronize.

  - If it does NOT overlap a known gap: this is a bit-flip in data we
    actually received (seen repeatedly: DQT length fields corrupted to
    huge garbage values while the real table data alongside is intact).
    For DQT specifically, substitute the known-correct length (67,
    confirmed from multiple real captures) and keep walking forward
    from THIS corrected position — never jump elsewhere in the file.

Usage:
    python3 smart_repair.py <input.jpg> <output.jpg>
"""
import sys
import pathlib

NO_LENGTH = {0x01, 0xD8, 0xD9, *range(0xD0, 0xD8)}
KNOWN_GOOD_LENGTH = {0xDB: 67}  # DQT segments on this satellite: always 67


def find_gaps(data, chunk=54):
    n_chunks = (len(data) + chunk - 1) // chunk
    gaps = []
    in_gap = False
    start = None
    for i in range(n_chunks):
        c = data[i*chunk:(i+1)*chunk]
        is_zero = c == b'\x00' * len(c)
        if is_zero and not in_gap:
            in_gap, start = True, i
        elif not is_zero and in_gap:
            in_gap = False
            gaps.append((start*chunk, i*chunk))
    if in_gap:
        gaps.append((start*chunk, n_chunks*chunk))
    return gaps


def overlaps_gap(pos, length, gaps):
    end = pos + length
    return any(pos < g_end and end > g_start for g_start, g_end in gaps)


def scan_markers_after(data, start):
    i = start
    n = len(data)
    while i < n - 1:
        if data[i] == 0xFF and data[i+1] not in (0x00, 0xFF):
            return i
        i += 1
    return None


def repair(data, gaps, verbose=True):
    out = bytearray()
    assert data[0:2] == b'\xff\xd8', "no SOI at start"
    out += data[0:2]
    pos = 2
    n = len(data)

    while pos < n - 1:
        if data[pos] != 0xFF:
            pos += 1
            continue
        code = data[pos+1]

        if code == 0xD9:
            out += data[pos:pos+2]
            if verbose: print(f"  [{pos}] EOI, done")
            return bytes(out)
        if code in NO_LENGTH:
            out += data[pos:pos+2]
            pos += 2
            continue

        if pos + 4 > n:
            if verbose: print(f"  [{pos}] not enough bytes for length, stop")
            break
        length = int.from_bytes(data[pos+2:pos+4], 'big')
        seg_total = 2 + length
        too_big = pos + seg_total > n or length < 2 or length > 1000

        if code == 0xDA:  # SOS: header + all remaining scan data
            seg_end = pos + seg_total
            if seg_end > n or overlaps_gap(pos, seg_total, gaps):
                if verbose: print(f"  [{pos}] SOS header corrupted, stop")
                break
            out += data[pos:seg_end] + data[seg_end:]
            if verbose: print(f"  [{pos}] SOS OK, copied {n-seg_end} bytes of scan data")
            return bytes(out)

        if too_big and code in KNOWN_GOOD_LENGTH:
            # Implausible length on a marker type we know the real
            # length for — this is a bit-flip, not missing data.
            # Fix it directly WITHOUT consulting gap overlap, since
            # overlap math built on a garbage length is meaningless
            # (a huge fake span will spuriously "overlap" gaps
            # anywhere else in the file even when this marker itself
            # is nowhere near one).
            fixed_len = KNOWN_GOOD_LENGTH[code]
            if verbose:
                print(f"  [{pos}] marker {code:02x} length={length} looks like a "
                      f"bit-flip -> assuming known-good length {fixed_len}")
            length = fixed_len
            seg_total = 2 + length
            out += data[pos:pos+2] + length.to_bytes(2, 'big') + data[pos+4:pos+seg_total]
            pos += seg_total
            continue

        gap_hit = overlaps_gap(pos, seg_total, gaps)

        if gap_hit or too_big:
            if verbose:
                print(f"  [{pos}] marker {code:02x} length={length}: "
                      f"gap_hit={gap_hit} too_big={too_big} -> resyncing")
            resume_from = pos + 2
            for g_start, g_end in gaps:
                if g_start <= pos < g_end or (pos < g_start < pos + max(seg_total, 4)):
                    resume_from = max(resume_from, g_end)
            nxt = scan_markers_after(data, resume_from)
            if nxt is None:
                if verbose: print(f"  [{pos}] no resync point found, stop")
                break
            pos = nxt
            continue

        out += data[pos:pos+seg_total]
        pos += seg_total

    return bytes(out) if len(out) > 2 else None


def main():
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <input.jpg> <output.jpg>")
        sys.exit(1)
    src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    data = src.read_bytes()
    gaps = find_gaps(data)
    print(f"[+] {len(data)} bytes, {len(gaps)} known gap(s): {gaps}")

    result = repair(data, gaps)
    if result is None:
        print("[!] repair failed")
        sys.exit(1)
    dst.write_bytes(result)
    print(f"[+] wrote {len(result)} bytes to {dst}")


if __name__ == '__main__':
    main()
