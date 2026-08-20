#!/usr/bin/env python3
"""
Splices a known-good JPEG header (from a donor file that's proven to
open, e.g. an earlier reception of the same satellite image) onto the
entropy-coded scan data of a different, corrupted-header reception —
on the theory that the camera's encoder uses fixed/unchanging header
settings, so the header boundary lands at the same byte offset in
both files as long as their total sizes match.

Usage:
    python3 splice_donor_header.py <donor.jpg> <corrupted.jpg> <output.jpg>
"""
import sys
import pathlib

NO_LENGTH = {0x01, 0xD8, 0xD9, *range(0xD0, 0xD8)}


def find_scan_start(data):
    """Walk markers TRUSTING their lengths (only valid for a known-good
    file) to find exactly where SOS's header ends / scan data begins."""
    pos = 2
    n = len(data)
    while pos < n - 1:
        if data[pos] != 0xFF:
            pos += 1
            continue
        code = data[pos+1]
        if code in NO_LENGTH:
            pos += 2
            continue
        length = int.from_bytes(data[pos+2:pos+4], 'big')
        if code == 0xDA:
            return pos + 2 + length
        pos += 2 + length
    return None


def main():
    if len(sys.argv) != 4:
        print(f"usage: {sys.argv[0]} <donor.jpg> <corrupted.jpg> <output.jpg>")
        sys.exit(1)
    donor_path, corrupt_path, out_path = (pathlib.Path(p) for p in sys.argv[1:4])

    donor = donor_path.read_bytes()
    corrupt = corrupt_path.read_bytes()

    print(f"[+] donor size: {len(donor)} bytes")
    print(f"[+] corrupted file size: {len(corrupt)} bytes")

    if len(donor) != len(corrupt):
        print("[!] WARNING: files are different sizes — header boundary "
              "may not land at the same offset. Proceeding anyway.")

    scan_start = find_scan_start(donor)
    if scan_start is None:
        print("[!] could not find SOS in donor — is it really a valid file?")
        sys.exit(1)
    print(f"[+] donor header is {scan_start} bytes (up to start of scan data)")

    result = donor[:scan_start] + corrupt[scan_start:]
    out_path.write_bytes(result)
    print(f"[+] wrote {len(result)} bytes to {out_path}")
    print(f"[+] ({scan_start} bytes from donor's header, "
          f"{len(result)-scan_start} bytes from your file's scan data)")


if __name__ == '__main__':
    main()
