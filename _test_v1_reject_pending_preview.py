import builtins, subprocess, tempfile, hashlib
from pathlib import Path
import MixFlowAssistant as m

work = Path(tempfile.mkdtemp(prefix="MixFlowV1_reject_"))
src = work / "reject_test.wav"
subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
                "-i", "aevalsrc=0.1*sin(2*PI*100*t)+0.1*sin(2*PI*1000*t):s=44100:d=3",
                "-c:a", "pcm_s24le", str(src)], check=True)
m.choose_file = lambda title: src
m.box = lambda *args, **kwargs: None
m.loudness_choice = lambda *args: ("OK", None)
answers = iter(["", "2", "bájale al beat", "2", "1"])
original_input = builtins.input
builtins.input = lambda prompt="": next(answers)
try:
    m.mezcla_mode()
finally:
    builtins.input = original_input

out_dir = m.OUT_ROOT / "Mezcla" / src.stem
rejected = list(out_dir.glob("REJECT_*_PREVIEW.wav"))
final = out_dir / (src.stem + "_MASTER_FINAL.wav")
assert rejected, "No se reconstruyó el preview tras rechazar el ajuste"
assert final.exists(), "No se generó el master final"
assert hashlib.sha256(final.read_bytes()).digest() == hashlib.sha256(rejected[-1].read_bytes()).digest(), "El master final no es idéntico al estado aceptado reconstruido"
print("PASS REJECTED_PREVIEW_REVERTS_TO_ACCEPTED_STATE")
