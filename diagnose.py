#!/usr/bin/env python3
"""
One command that automatically tries to make sense of / fix an
invalid decoded image, instead of remembering find_gaps.py,
smart_repair.py, patch_dqt_length.py as separate manual steps.

Usage:
    python3 diagnose.py <file.jpg>
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from alferov_lib import check_image, format_summary
import smart_repair


def main():
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <file.jpg>")
        sys.exit(1)

    path = pathlib.Path(sys.argv[1])
    info = check_image(path)
    print(format_summary(info))

    if info["valid"]:
        print("  Nothing to do — already valid.")
        return

    if not info["has_soi"]:
        print("  No SOI marker at all — this file is missing its start "
              "entirely. No automated repair can help; you need a "
              "different/additional recording that actually captured "
              "the beginning of this image's transmission.")
        return

    print(f"  {len(info['gaps'])} gap(s), {info['missing_bytes']} bytes "
          f"missing. Attempting automatic repair...")

    data = path.read_bytes()
    gaps = smart_repair.find_gaps(data)
    result = smart_repair.repair(data, gaps, verbose=False)

    if result is None:
        print("  Automatic repair failed to produce output.")
        print("  Next step: find another recording of this same image "
              "number to merge in more data, or try "
              "splice_donor_header.py with a known-good file of the "
              "same satellite if you have one.")
        return

    repaired_path = path.with_name(path.stem + "_diagnosed.jpg")
    repaired_path.write_bytes(result)
    repaired_info = check_image(repaired_path)

    if repaired_info["valid"]:
        print(f"  SUCCESS — repaired version is valid: {repaired_path}")
    else:
        print(f"  Repair attempted but result still isn't valid: {repaired_path}")
        print(f"  ({repaired_info['error']})")
        print("  Next step: find another recording of this same image "
              "number to merge in more data, or try "
              "splice_donor_header.py with a known-good file of the "
              "same satellite if you have one.")


if __name__ == '__main__':
    main()
