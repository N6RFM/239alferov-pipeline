#!/usr/bin/env python3
"""
Scans a decoded 239Alferov .jpg for zero-filled 54-byte gaps (chunks
that were never received), so you can see exactly how complete a file
is and where the holes are.

Usage:
    python3 find_gaps.py <path/to/file.jpg>

(Thin CLI wrapper — the actual gap-finding logic lives in
alferov_lib.py, shared with status.sh and diagnose.py so there's one
source of truth instead of duplicated implementations.)
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from alferov_lib import find_gaps


def main():
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <path/to/file.jpg>")
        sys.exit(1)

    f = pathlib.Path(sys.argv[1]).expanduser()
    data = f.read_bytes()
    print(f"file: {f}")
    print(f"file size: {len(data)} bytes")

    gaps = find_gaps(data)
    total_missing = sum(end - start for start, end in gaps)
    print(f"{len(gaps)} likely gap(s) (runs of all-zero 54-byte chunks), "
          f"{total_missing} bytes missing total:")
    for start, end in gaps:
        print(f"  byte offset {start} .. {end}  ({(end-start)//54} chunk(s) missing)")

    if not data.startswith(b'\xff\xd8'):
        print("WARNING: file doesn't even start with a valid JPEG SOI marker.")
    if not (data.endswith(b'\xff\xd9') or b'\xff\xd9' in data[-200:]):
        print("NOTE: no EOI (end-of-image) marker found near the end — "
              "the final chunk(s) of this image likely haven't arrived yet.")


if __name__ == '__main__':
    main()
