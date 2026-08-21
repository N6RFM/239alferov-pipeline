#!/usr/bin/env python3
"""
Surgical fix for the specific corruption we keep hitting: DQT segment
length fields (right after 'FF DB') get bit-flipped during reception,
even though the actual table DATA and everything else in the header
is fine. This satellite sends TWO DQT segments (luma + chroma) and
both tend to get hit the same way. Rather than replacing the whole
header with an unrelated donor image's (which imports wrong colors),
this patches every implausible DQT length field with the correct
value, then you re-run repair_jpeg.py on the result.

Usage:
    python3 patch_dqt_length.py <input.jpg> <output.jpg> [correct_length]

If correct_length isn't given, defaults to 67 (0x0043) — confirmed
correct for both this satellite's DQT segments from a known-good file.
Any DQT segment whose declared length is already <1000 (plausible) is
left untouched.
"""
import sys
import pathlib

def main():
    if len(sys.argv) < 3:
        print(f"usage: {sys.argv[0]} <input.jpg> <output.jpg> [correct_length]")
        sys.exit(1)
    src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    correct_length = int(sys.argv[3]) if len(sys.argv) > 3 else 67

    data = bytearray(src.read_bytes())
    n_patched = 0
    pos = 0
    while True:
        pos = data.find(b'\xff\xdb', pos)
        if pos == -1:
            break
        old_length = int.from_bytes(data[pos+2:pos+4], 'big')
        if old_length > 1000:  # implausible for a real DQT segment
            print(f"[+] DQT marker at byte {pos}: garbage length={old_length} -> patching to {correct_length}")
            data[pos+2:pos+4] = correct_length.to_bytes(2, 'big')
            n_patched += 1
        else:
            print(f"[+] DQT marker at byte {pos}: length={old_length} looks plausible, leaving as-is")
        pos += 2

    if n_patched == 0:
        print("[!] no implausible DQT lengths found — nothing patched")

    dst.write_bytes(bytes(data))
    print(f"[+] patched {n_patched} segment(s), wrote {dst}")
    print(f"[+] now run repair_jpeg.py on this file to resync past the "
          f"remaining known gaps:")
    print(f"    python3 repair_jpeg.py {dst} {dst.with_name(dst.stem + '_repaired.jpg')}")

if __name__ == '__main__':
    main()
