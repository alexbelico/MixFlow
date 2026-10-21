# MixFlow

Local, open-source mixing and mastering assistant for independent producers. Everything runs on your own Windows PC: no cloud, no uploads, and your original audio files are never modified.

## What it does

MixFlow has two modes:

- **MIX**: load a finished stereo mix.
- **STEMS**: load separate stems (vocals, backs, adlibs, beat, ...).

### Features

- **Analysis before processing**: integrated loudness (LUFS), loudness range, true peak, spectral bands, crest factor, DC offset, stereo correlation, mid/side ratio, low-level regions and energy changes.
- **Adaptive processing**: a conservative EQ and dynamics recipe built from the measured spectrum.
- **Loudness targets**: Light (-14 LUFS), Basic (-12), Habitual (-10), High (-8), Custom, or no change. If a target cannot be reached within tolerance without exceeding the true-peak ceiling, MixFlow tells you and asks for another level.
- **Natural-language feedback** (Spanish), for example "bájale al beat" or "súbele el volumen a los adlibs".
- **Preview, accept, reject and multi-step undo**: every change is rebuilt from the untouched original, so degraded renders never accumulate.
- **STEMS mode**:
  - tolerant stem classification (lead vocal, second vocal, adlibs, backs, beat, alignment reference) with manual correction
  - alignment of stems using RMS envelopes
  - per-stem gain and processing
  - optional export of the processed vocal stems
  - note-by-note vocal pitch correction (AFINAR), always started explicitly by the user, with adjustable intensity and a preview before accepting
- **WAV export** of the final master.
- **Safe cleanup**: only the temporary files created in the current session are deleted.

## Status

V1 is functionally complete for its documented scope. The automated tests use synthetic signals; validation on real songs is still in progress. Spectral edits on a stereo mix are approximate: they can affect other instruments that share the same frequency band.

## Requirements

- Windows
- Python 3.10 or newer (with the `py` launcher)
- [FFmpeg](https://ffmpeg.org/) available in your `PATH`. For the best pitch-correction quality, use an FFmpeg build that includes the `rubberband` filter (for example the "full" builds); without it, MixFlow falls back to a simpler method.

FFmpeg is **not** bundled with this repository. Install it yourself; its own license applies.

## Installation

```bash
git clone https://github.com/alexbelico/MixFlow.git
cd MixFlow
pip install -r requirements.txt
```

## Usage

Double-click `MixFlow.bat` to open the graphical interface (it starts `MixFlowGUI.py` without a console window). You can also run it directly:

```bash
py MixFlowGUI.py
```

Then:

1. Choose MIX or STEMS and drop your files in.
2. Review the analysis and the proposed adjustments.
3. Listen to the preview, then accept, reject or undo.
4. Choose a loudness target and export the master.

## Tests

```bash
set PYTHONUTF8=1
python _run_v1_suite.py
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).
