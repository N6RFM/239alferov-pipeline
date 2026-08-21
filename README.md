# 239Alferov Image Decoding Pipeline

Tools for decoding GEOSCAN-framed images from the 239Alferov satellite
(a student-built educational CubeSat, Geoscan program) from
pre-recorded audio — SatNOGS observations, or your own SDR recordings
— using [UZ7HO's soundmodem](http://uz7.ho.ua/packetradio.htm) for
FSK demodulation and [baskiton's SatsDecoder](https://github.com/baskiton/SatsDecoder)
decoding classes driven headlessly (no GUI required).

**Status: working.** This pipeline has successfully decoded complete,
valid images from real SatNOGS recordings. It was built iteratively
while debugging real reception and decoding problems — the "Known
issues we hit and fixed" section below is worth reading, since it
explains real bugs (including one serious one in this pipeline
itself) that cost a lot of time to track down.

## What this does and doesn't do

- **Does:** take an audio recording (`.mp3`/`.ogg`/`.wav`, already
  FM-demodulated — e.g. a SatNOGS observation download) and decode any
  GEOSCAN image chunks in it into `.jpg` files, merging chunks from
  multiple separate recordings of the same image over time.
- **Does not:** do FM demodulation itself, or receive live RF. You need
  an already-demodulated audio *file* to feed it. Live reception would
  require routing a live SDR receiver's demodulated audio into the
  virtual sink this pipeline uses, instead of a recording — untested,
  a future direction.

## What you'll actually get

239Alferov transmits more than Earth-observation photos — it's an
educational mission, and student teams commonly beam down artwork,
drawings, and "postcard" images as part of outreach. Don't be
surprised if a fully, cleanly decoded image turns out to be a painted
portrait or a hand-drawn illustration rather than a photo of Earth —
that's the mission working as intended, not a decoding problem.

## Prerequisites

- Ubuntu/Debian-based Linux (tested on Ubuntu 24.04)
- `sudo` access (for package installs and one-time port cleanup)
- PulseAudio (standard on most desktop Ubuntu installs)

## One-time setup

```bash
git clone https://github.com/N6RFM/239alferov-pipeline.git
cd 239alferov-pipeline
./setup.sh
```

This installs Wine, downloads soundmodem, clones SatsDecoder, installs
its light Python dependencies (`construct`, `Pillow`, `numpy<2`), and
creates a virtual PulseAudio sink (`Alferov_Pipeline`) used to route
recordings into soundmodem as if they were live audio input. All
scripts auto-detect their own location (`WORKDIR`), so this works
wherever you clone it — no path editing needed.

## Normal usage

**One file:**
```bash
./go.sh path/to/recording.ogg
```

**Multiple files, one after another** (interactive picker or explicit list):
```bash
./batch.sh                          # lists recordings in the folder, pick by number/range/"all"
./batch.sh file1.ogg file2.ogg      # or name them directly
./batch.sh *.ogg                    # or a glob
```

**Continuous live monitoring** (no file — pairs with a live audio source instead of a recording, e.g. the `A239Alferov_with_audio.grc` flowgraph in this repo, which streams live demodulated audio straight from your SDR into the `Alferov_Pipeline` virtual sink):
```bash
./monitor.sh
```
Unlike `go.sh`/`batch.sh`, this doesn't play anything or stop on its own —
it just connects to soundmodem and keeps writing chunks to disk for as
long as it runs. Stop with Ctrl+C. For multi-day unattended operation,
run it inside `tmux`/`screen` so it survives your terminal closing, or
just leave the terminal open if that's not a concern.

## Live reception (continuous, multi-day)

`A239Alferov_with_audio.grc` is a modified version of the original live
GNU Radio flowgraph — same Airspy source, mixer, low-pass filter, and
Doppler tracking as before, with three blocks added as a parallel
branch off the existing filtered signal:

```
low_pass_filter_0 -> Quadrature Demod -> Rational Resampler -> Audio Sink
```

This streams continuously demodulated FM audio directly into
soundmodem, in real time, for as long as the flowgraph runs — no
recording, no file I/O, no waiting. It also includes an `Import` block
(`import_pulse_sink_0`) that sets `PULSE_SINK=alferov_pipe` from
inside the flowgraph itself, so it's routed correctly whether you
launch it by double-clicking, hitting Execute in GRC, or running the
generated `.py` directly — no manual environment variable needed.

**To use it for real multi-day monitoring:**

1. Open `A239Alferov_with_audio.grc` in GNU Radio Companion and Execute
   it (or run the generated `.py`). Leave it running.
2. Make sure soundmodem is running and configured (see setup above).
3. In a separate terminal (ideally inside `tmux`/`screen` for real
   multi-day resilience), run:
   ```bash
   ./monitor.sh
   ```
4. Check progress any time with `./status.sh`, without needing to stop
   anything.

The flowgraph itself doesn't gate on pass timing — it streams
continuously whether or not the satellite is actually overhead, which
is harmless (noise essentially never passes GEOSCAN's framing checks)
but does mean it runs 24/7 rather than only during scheduled passes.

**First run ever:** soundmodem opens and you configure it once —

- Protocol: `GEOSCAN 2.7 9600bd`
- Input device: `Monitor of Alferov_Pipeline`
- KISS Server: **enabled** (the checkbox, not just the port number — easy to miss), port `8100`

(soundmodem has no frequency setting — it only processes audio, it
never tunes anything. That's handled upstream, wherever the
recording/audio actually came from.)

Every run after that reuses the already-configured, already-running
soundmodem instance automatically — no window, no reconfiguration —
as long as you don't close it. If it gets closed, the next run detects
that and walks you through reconfiguring once. Force a clean restart
any time with `./go.sh --reset <file>`.

Output lands in `decoded_output/`, with a validity check printed at
the end of every run, checked directly against the files on disk.

## How merging across recordings works

Real transmissions rarely fit in one recording. This pipeline uses a
**stable filename per image number** (e.g. `239ALFEROV_N1.jpg`, no
timestamp) so that running it against a *different* recording of the
same image on a different day writes into the *same* file, filling in
whatever chunks were missing before — rather than producing a new
fragment every time.

## Scripts

| Script | Purpose |
|---|---|
| `alferov` | Single entry point wrapping everything below — `./alferov {setup\|decode\|batch\|monitor\|status\|diagnose\|cleanup}` |
| `setup.sh` | One-time install of soundmodem, Wine, SatsDecoder, audio sink |
| `go.sh` | Decode one recording (includes a preflight duration check and validity report) |
| `batch.sh` | Decode several recordings in sequence (interactive picker or file list) |
| `monitor.sh` | Continuous live monitoring — no file, connects to soundmodem and stays connected until Ctrl+C. For live-audio setups, not recorded files |
| `A239Alferov_with_audio.grc` | Live GNU Radio flowgraph: Airspy + Doppler tracking + streams demodulated audio straight into soundmodem, continuously, no file I/O |
| `status.sh` | Report validity/gap status of everything already in `decoded_output/`, no decoding |
| `diagnose.py` | Auto-diagnose an invalid image and attempt repair in one step |
| `play_recording.sh` | Called internally by `go.sh` — converts and plays a recording into the virtual sink |
| `kiss_tcp_decode.py` | The actual headless decoder — connects to soundmodem's KISS server, runs SatsDecoder's real classes |
| `alferov_lib.py` | Shared validity/gap-checking logic used by `status.sh`, `go.sh`, and `diagnose.py` |
| `cleanup.sh` | Archives (doesn't delete) old logs, cached audio, and superseded fragments |
| `find_gaps.py` | Standalone CLI for gap-checking a single file (thin wrapper around `alferov_lib.py`) |
| `smart_repair.py` | JPEG marker-repair: resyncs around real gaps and fixes known bit-flip patterns (e.g. corrupted DQT lengths) in one pass |
| `splice_donor_header.py` | Grafts a known-good file's header onto another file's scan data, for cases `smart_repair.py` can't fix on its own |

## Known issues we hit and fixed

**The big one — a KISS escaping bug in this pipeline itself.**
`kiss_tcp_decode.py`'s stream parser was splitting KISS frames on the
`0xC0` delimiter but never implementing the *escaping* half of the
KISS protocol. Any literal `0xDB` byte in real data must be sent over
KISS as `0xDB 0xDD` so it isn't confused with the escape byte itself
— and JPEG's DQT marker is literally `0xFF 0xDB`. That meant **every
quantization table marker in every image, across every recording this
pipeline ever decoded, was corrupted by our own code**, not by the
satellite or the radio link. Most of the "corrupted/unopenable image"
struggles documented in this project's history turned out to trace
back to this one bug. It's fixed now (see `KissStreamParser` in
`kiss_tcp_decode.py`) — `smart_repair.py` and `splice_donor_header.py`
were built while tracking this down and are kept as reference/fallback
repair tools, but shouldn't be needed for newly-decoded files.

**Other real limitations, still true:**

- **Single recordings rarely contain a full image.** Plan to merge
  multiple recordings, not expect completion from one file.

- **The satellite reuses image-number slots (N0–N9ish) for different,
  unrelated photos over time.** Merging two recordings of the same
  slot number from days apart can produce a garbled overlay of two
  *different* images. Same-day recordings are much safer merge
  candidates.

- **Missing chunks vs. corrupted chunks are different problems.**
  `find_gaps.py` only catches fully-missing data (clean zero runs).
  Bit errors in chunks that were technically *received* don't show up
  as gaps at all — they just silently corrupt whatever they touch.

- **Occasional misdecoded noise** shows up as images with absurd
  numbers (`N256`, `N1024`, etc.) — `kiss_tcp_decode.py` filters these
  out automatically now (anything with fnum ≥ 20 is discarded before
  it's even handed to the decoder).

- **soundmodem doesn't persist its settings between fresh launches.**
  You'll need to reconfigure the 4 items above every time it's closed
  and reopened — a limitation of the underlying tool, not something
  scriptable around reliably.

## Author

Built by [N6RFM](https://github.com/N6RFM), developed in an extended
collaborative debugging session with Claude (Anthropic) — from initial
GNU Radio flowgraph troubleshooting through discovering and fixing the
KISS escaping bug that turned out to be the real root cause of most of
this project's early struggles.

## Credits

- [SatsDecoder](https://github.com/baskiton/SatsDecoder) by baskiton
  (GPL-3.0/MIT) — the real GEOSCAN decoding logic used here, driven
  headlessly rather than through its GUI.
- [High-Speed SoundModem](http://uz7ho.org.ua/hs.htm) by UZ7HO — FSK
  demodulation and GEOSCAN deframing.
- Community troubleshooting and protocol details from the
  [Libre Space Community thread on 239Alferov image transmissions](https://community.libre.space/t/239alferov-image-transmissions/15156).
