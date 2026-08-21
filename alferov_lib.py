#!/usr/bin/env python3
"""
Shared diagnostic logic used by status.sh, go.sh's output check, and
diagnose.py, so all three agree on what "valid" and "how broken" mean
for a decoded image.
"""
import pathlib
from PIL import Image


def find_gaps(data: bytes, chunk=54):
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


def check_image(path) -> dict:
    """Returns a dict describing exactly what's known about one file:
    size, whether it opens as a valid image, and if not, how many
    bytes/chunks are missing and whether it has an end marker."""
    path = pathlib.Path(path)
    data = path.read_bytes()
    result = {
        "path": str(path),
        "name": path.name,
        "size": len(data),
        "valid": False,
        "error": None,
        "gaps": [],
        "missing_bytes": 0,
        "has_soi": data[:2] == b'\xff\xd8',
        "has_eoi": data[-2:] == b'\xff\xd9' or b'\xff\xd9' in data[-200:],
    }
    try:
        Image.open(path).verify()
        result["valid"] = True
    except Exception as e:
        result["error"] = str(e)
        gaps = find_gaps(data)
        result["gaps"] = gaps
        result["missing_bytes"] = sum(end - start for start, end in gaps)
    return result


def format_summary(info: dict) -> str:
    if info["valid"]:
        return f"  {info['name']} ({info['size']} bytes) -> VALID"
    bits = [f"{info['size']} bytes", f"{len(info['gaps'])} gap(s)",
            f"{info['missing_bytes']}b missing"]
    if not info["has_soi"]:
        bits.append("NO SOI")
    if not info["has_eoi"]:
        bits.append("NO EOI")
    return f"  {info['name']} -> INVALID ({', '.join(bits)}) [{info['error']}]"


if __name__ == '__main__':
    import sys
    for p in sys.argv[1:]:
        print(format_summary(check_image(p)))
