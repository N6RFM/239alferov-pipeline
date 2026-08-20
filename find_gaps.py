import os

f = os.path.expanduser("~/alferov_pipeline/decoded_output/239ALFEROV_N3_2026-08-20T19-34-10Z.jpg")
data = open(f, "rb").read()
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

print(f"{len(gaps)} likely gap(s) (runs of all-zero 54-byte chunks):")
for start, end in gaps:
    print(f"  byte offset {start} .. {end}  ({(end-start)//CHUNK} chunk(s) missing)")
