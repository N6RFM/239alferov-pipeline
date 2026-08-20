#!/usr/bin/env python3
"""
Scans a decoded 239Alferov .jpg for zero-filled 54-byte gaps (chunks
that were never received), so you can see exactly how complete a file
is and where the holes are.

Usage:
    python3 find_gaps.py <path/to/file.jpg>
"""
import sys
import os

def main():
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <path/to/file.jpg>")
        sys.exit(1)

    f = os.path.expanduser(sys.argv[1])
    data = open(f, "rb").read()
    print(f"file: {f}")
    print(f"file size: {len(data)} bytes")

    CHUNK = 54
    n_chunks = (len(data) + CHUNK - 1) // CHUNK
    gaps = []
    in_gap = False
    gap_start = None

    for i in range(n_chunks):
        chunk = data[i*CHUNK:(i+1)*CHUNK]
        is_zero = chunk == b'\x00' * len(chunk)
        if is_zero and not in_gap:
            in_gap = True
            gap_start = i
        elif not is_zero and in_gap:
            in_gap = False
            gaps.append((gap_start * CHUNK, i * CHUNK))
    if in_gap:
        gaps.append((gap_start * CHUNK, n_chunks * CHUNK))

    total_missing = sum(end - start for start, end in gaps)
    print(f"{len(gaps)} likely gap(s) (runs of all-zero 54-byte chunks), "
          f"{total_missing} bytes missing total:")
    for start, end in gaps:
        print(f"  byte offset {start} .. {end}  ({(end-start)//CHUNK} chunk(s) missing)")

    if not data.startswith(b'\xff\xd8'):
        print("WARNING: file doesn't even start with a valid JPEG SOI marker.")
    if not data.endswith(b'\xff\xd9') and b'\xff\xd9' not in data[-200:]:
        print("NOTE: no EOI (end-of-image) marker found near the end — "
              "the final chunk(s) of this image likely haven't arrived yet.")

if __name__ == '__main__':
    main()
