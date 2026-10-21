# MixFlow

Local open-source audio mixing and mastering tool.

It analyzes loudness (LUFS and true peak), applies adaptive EQ and dynamics, supports stem classification and alignment, and includes preview with accept/undo. All processing runs locally.

## Features

- Loudness analysis and target levels (Light, Basic, Habitual, High, Custom)
- Adaptive EQ and dynamics with preview, accept, and undo
- Stem classification and RMS-based alignment
- Stereo diagnostics (correlation, mid/side, low-level regions)
- Safe intermediate file cleanup
- Automated test suite (synthetic signals)

## Status

V1 is under active validation. Autotune/pitch correction was removed on 2026-10-09. Tests currently pass on synthetic signals; real-world audible validation is still in progress.

## Installation

Requires Python 3.x.

```bash
git clone https://github.com/alexbelico/MixFlow.git
cd MixFlow
pip install -r requirements.txt
```

Run the main script according to your launcher (`.bat` / `.vbs` or directly via Python).

## Usage

1. Load stems or a stereo track.
2. Run analysis and apply proposed adjustments.
3. Preview, accept, or undo.
4. Export the result.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
