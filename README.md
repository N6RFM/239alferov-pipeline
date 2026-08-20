# 239Alferov Image Decoding Pipeline (experimental)

Tools for decoding GEOSCAN-framed images from the 239Alferov satellite
from pre-recorded audio (SatNOGS observations, or your own SDR
recordings), using [UZ7HO's soundmodem](http://uz7.ho.ua/packetradio.htm)
for FSK demodulation and [baskiton's SatsDecoder](https://github.com/baskiton/SatsDecoder)
decoding classes driven headlessly (no GUI required).

**Status: experimental / work-in-progress.** This was built iteratively
while debugging real reception gaps, not designed up front — read the
"Known limitations" section before assuming it'll just work on the
first try.

## What this does and doesn't do

- **Does:** take an audio recording (`.mp3`/`.ogg`/`.wav`, already
  FM-demodulated — e.g. a SatNOGS observation download) and decode any
  GEOSCAN image chunks in it into `.jpg` files, merging chunks from
  multiple separate recordings of the same image over time.
- **Does not:** do FM demodulation itself, or receive live RF. You need
  an already-demodulated audio *file* to feed it. Live reception would
  require routing a live SDR receiver's demodulated audio into the
  virtual sink this pipeline uses, instead of a recording — untested,
  noted as a future direction.

## Prerequisites

- Ubuntu/Debian-based Linux (tested on Ubuntu 24.04)
- `sudo` access (for package installs and one-time port cleanup)
- PulseAudio (standard on most desktop Ubuntu installs)

## One-time setup

```bash
git clone <this-repo> ~/alferov_pipeline
cd ~/alferov_pipeline
./setup.sh
```

This installs Wine, downloads soundmodem, clones SatsDecoder, installs
its light Python dependencies (`construct`, `Pillow`, `numpy<2`), and
creates a virtual PulseAudio sink (`Alferov_Pipeline`) used to route
recordings into soundmodem as if they were live audio input.

## Normal usage

```bash
./go.sh path/to/recording.ogg
```

First run: soundmodem opens and you configure it once —

- Protocol: `GEOSCAN 2.7 9600bd`
- Frequency: `436.270 MHz`
- Input device: `Monitor of Alferov_Pipeline`
- KISS Server: enabled, port `8100`

**The KISS Server checkbox specifically must be checked** — it's easy
to only set the port number and forget to enable it, which causes the
decoder to connect successfully but receive nothing (see Known
limitations).

Every run after that reuses the already-configured, already-running
soundmodem instance automatically — no window, no reconfiguration —
*as long as you don't close it*. If soundmodem gets closed or killed,
the next `./go.sh` call will detect that and walk you through
reconfiguring once.

If something's stuck (port conflicts, a hung process from a previous
run), force a clean restart:

```bash
./go.sh --reset path/to/recording.ogg
```

Output lands in `decoded_output/`, with a validity check printed at
the end of every run (checked directly against the file on disk, not
relying on any internal summary that may not always print reliably).

## How merging across recordings works

Real transmissions rarely fit in one recording. This pipeline forces
a **stable filename per image number** (e.g. `239ALFEROV_N3.jpg`, no
timestamp) so that running `go.sh` against a *different* recording of
the same image on a different day writes into the *same* file,
filling in whatever chunks were missing before — rather than
producing a new fragment every time. This required patching around a
quirk in SatsDecoder's own filename generator, which stamps a fresh
timestamp on every run even with its own merge mode enabled; see
`kiss_tcp_decode.py`'s `patch_stable_filenames()` for details.

## Tools for diagnosing/salvaging partial images

Real reception is messy. These are for when `decoded_output/*.jpg`
exists but won't open, or you want to understand exactly what's wrong
with it before giving up on a file:

- **`find_gaps.py <file.jpg>`** — scans for zero-filled 54-byte runs
  (the satellite's chunk size), reporting exactly which byte ranges
  were never received. Useful for judging how close a file is to
  complete, and for spotting a second recording worth merging in.

- **`repair_jpeg.py <in.jpg> <out.jpg>`** — walks JPEG markers,
  distrusting any segment that overlaps a known gap (from
  `find_gaps.py`'s logic) instead of blindly trusting a possibly
  garbage length field, and tries to resynchronize past it. Works when
  the corruption is cleanly bounded to known missing chunks; does
  **not** help with bit-flip corruption in chunks that were actually
  received (see Known limitations).

- **`splice_donor_header.py <donor.jpg> <corrupted.jpg> <out.jpg>`** —
  if you have an older/different reception of *the same image number*
  that opens fine, this grafts its known-good header (quantization/
  Huffman tables) onto your file's actual scan data, on the theory
  that a fixed camera uses the same encoder settings for every shot.
  Works when the corruption is in the header (e.g. a garbled DQT
  length field); irrelevant if the header's already fine.

## Known limitations (learned the hard way)

- **Single recordings rarely contain a full image.** A 10-minute pass
  typically covers a fraction of what a full transmission needs — plan
  to merge multiple recordings, not expect completion from one file.

- **The satellite reuses image-number slots (N0–N9ish) for different,
  unrelated photos over time.** Merging two recordings of "N3" from
  days apart can produce a garbled overlay of two *different* photos,
  not a cleaner version of one. Same-day recordings are much safer
  merge candidates than ones from unrelated dates.

- **Missing chunks vs. corrupted chunks are different problems.**
  `find_gaps.py` only catches fully-missing data (clean zero runs).
  Bit errors in chunks that were technically *received* (e.g. from
  marginal SNR) don't show up as gaps at all — they just silently
  corrupt whatever they touch, and are far harder to detect or fix
  after the fact.

- **soundmodem doesn't persist its settings between fresh launches.**
  You'll need to reconfigure the 4 items above every time it's closed
  and reopened — this is a limitation of the underlying tool, not
  something scriptable around reliably.

- **The decoder's own shutdown/summary print is not fully reliable**
  under signal-based termination in all cases observed — `go.sh`
  therefore always does a final validity check directly against the
  files in `decoded_output/`, independent of that summary.

## Credits

- [SatsDecoder](https://github.com/baskiton/SatsDecoder) by baskiton
  (GPL-3.0/MIT) — the real GEOSCAN decoding logic used here, driven
  headlessly rather than through its GUI.
- [High-Speed SoundModem](http://uz7ho.org.ua/hs.htm) by UZ7HO — FSK
  demodulation and GEOSCAN deframing.
- Community troubleshooting and protocol details from the
  [Libre Space Community thread on 239Alferov image transmissions](https://community.libre.space/t/239alferov-image-transmissions/15156).
