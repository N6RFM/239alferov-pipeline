#!/usr/bin/env python3
"""
Surgical JPEG repair for files with a small number of KNOWN, isolated
zero-filled gaps (from missing 54-byte satellite chunks).

Strategy: brute-force scan the ENTIRE file for every plausible JPEG
marker position (FF followed by a valid marker code), independent of
trusting any single length field. Then walk forward from SOI picking
the marker chain that stays self-consistent (each marker's declared
length correctly lands on the next real marker), silently DROPPING
any segment that overlaps a known corrupted gap instead of trusting
its garbage length field. This lets parsing resynchronize past the
damage instead of derailing completely, as standard decoders do.

This can't invent missing pixel/table data — it just stops the
corruption from taking down markers/data that were actually fine.
Success isn't guaranteed, especially if the gap falls inside the
entropy-coded scan data itself rather than the header.

Usage:
    python3 repair_jpeg.py <input.jpg> <output.jpg>
"""
import sys
import pathlib

# Markers with NO length field following them
NO_LENGTH = {0x01, 0xD8, 0xD9, *range(0xD0, 0xD8)}  # TEM, SOI, EOI, RSTn


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


def scan_markers(data):
    """Every position i where data[i]==0xFF and data[i+1] looks like
    a real marker code (not 0x00 stuffing, not fill 0xFF)."""
    candidates = []
    i = 0
    n = len(data)
    while i < n - 1:
        if data[i] == 0xFF and data[i+1] not in (0x00, 0xFF):
            candidates.append(i)
        i += 1
    return candidates


def repair(data, gaps, verbose=False):
    out = bytearray()
    assert data[0:2] == b'\xff\xd8', "no SOI at start — can't repair"
    out += data[0:2]
    pos = 2
    n = len(data)

    while pos < n - 1:
        if data[pos] != 0xFF:
            pos += 1
            continue
        code = data[pos+1]
        if code == 0xD9:  # EOI
            if verbose:
                print(f"  [{pos}] EOI, done")
            out += data[pos:pos+2]
            return bytes(out)
        if code in NO_LENGTH:
            if verbose:
                print(f"  [{pos}] marker {code:02x}, no length, copy 2 bytes")
            out += data[pos:pos+2]
            pos += 2
            continue
        if code == 0xDA:  # SOS
            if pos + 4 > n:
                if verbose:
                    print(f"  [{pos}] SOS but not enough bytes for header, stop")
                break
            length = int.from_bytes(data[pos+2:pos+4], 'big')
            seg_end = pos + 2 + length
            if verbose:
                print(f"  [{pos}] SOS, header length={length}, seg_end={seg_end}, "
                      f"overlaps_gap={overlaps_gap(pos, 2+length, gaps)}")
            if seg_end > n or overlaps_gap(pos, 2+length, gaps):
                if verbose:
                    print(f"  [{pos}] SOS header itself corrupted, stop")
                break
            out += data[pos:seg_end]
            out += data[seg_end:]
            if verbose:
                print(f"  [{pos}] SOS OK, copied rest of file "
                      f"({n - seg_end} bytes of scan data)")
            return bytes(out)

        if pos + 4 > n:
            if verbose:
                print(f"  [{pos}] marker {code:02x}, not enough bytes for length, stop")
            break
        length = int.from_bytes(data[pos+2:pos+4], 'big')
        seg_total = 2 + length
        bad = overlaps_gap(pos, seg_total, gaps) or pos + seg_total > n or length < 2
        if verbose:
            print(f"  [{pos}] marker {code:02x}, length={length}, "
                  f"seg_total={seg_total}, end={pos+seg_total}, bad={bad}")
        if bad:
            resume_from = pos + 2
            for g_start, g_end in gaps:
                if g_start <= pos < g_end or (pos < g_start < pos + max(seg_total, 4)):
                    resume_from = max(resume_from, g_end)
            candidates = [c for c in scan_markers(data) if c >= resume_from]
            if verbose:
                print(f"  [{pos}] BAD segment, resume_from={resume_from}, "
                      f"{len(candidates)} resync candidate(s): {candidates[:5]}")
            if not candidates:
                if verbose:
                    print(f"  [{pos}] no resync candidates found, stop")
                break
            pos = candidates[0]
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

    result = repair(data, gaps, verbose=True)
    if result is None:
        print("[!] repair failed — could not produce usable output")
        sys.exit(1)

    dst.write_bytes(result)
    print(f"[+] wrote {len(result)} bytes to {dst}")
    print("[+] now try opening it — e.g.:")
    print(f"    convert {dst} {dst.with_suffix('.png')}")


if __name__ == '__main__':
    main()
