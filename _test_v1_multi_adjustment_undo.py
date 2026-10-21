import builtins, subprocess, tempfile, hashlib
from pathlib import Path
import MixFlowAssistant as m

work=Path(tempfile.mkdtemp(prefix="MixFlowV1_multi_undo_"))
src=work/"undo_mix.wav"
subprocess.run(["ffmpeg","-y","-hide_banner","-loglevel","error","-f","lavfi","-i",
                "aevalsrc=0.1*sin(2*PI*100*t)+0.1*sin(2*PI*1000*t):s=44100:d=3",
                "-c:a","pcm_s24le",str(src)],check=True)
m.choose_file=lambda title:src
m.box=lambda *args,**kwargs:None
m.loudness_choice=lambda *args:("OK",None)
answers=iter(["","2","bajale al beat","1","2","subele al beat","1","3","1"])
old=builtins.input
builtins.input=lambda prompt="":next(answers)
try:
    m.mezcla_mode()
finally:
    builtins.input=old
out=m.OUT_ROOT/"Mezcla"/src.stem
undo=list(out.glob("UNDO_*_PREVIEW.wav"))
final=out/"undo_mix_MASTER_FINAL.wav"
assert undo, "Undo render missing after two accepted adjustments"
assert final.exists(), "Final master missing"
assert hashlib.sha256(final.read_bytes()).digest()==hashlib.sha256(undo[-1].read_bytes()).digest(), "Final master does not match the undo-restored state"
print("PASS MULTI_ACCEPTED_ADJUSTMENTS_UNDO_RESTORES_PREVIOUS_STATE")
