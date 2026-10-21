import builtins, tempfile, wave
from pathlib import Path
import numpy as np
import MixFlowAssistant as m

work=Path(tempfile.mkdtemp(prefix="MixFlowV1_many_stems_"))
sr=44100
t=np.arange(sr*3)/sr
def make(name,freq):
    p=work/name
    x=0.06*np.sin(2*np.pi*freq*t)
    pcm=np.column_stack([x,x]).clip(-1,1)
    pcm=(pcm*32767).astype("<i2")
    with wave.open(str(p),"wb") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sr); wf.writeframes(pcm.tobytes())
    return p
files=[
 make("lead_verse.wav",220),
 make("second_verse.wav",260),
 make("main_chorus.wav",330),
 make("second_chorus.wav",390),
 make("adlibs_take.wav",440),
 make("backs_remarques.wav",500),
 make("beat_instrumental.wav",110),
 make("alignment_reference.wav",220)
]
original_hashes={p:__import__("hashlib").sha256(p.read_bytes()).digest() for p in files}
m.choose_files=lambda title:files
m.box=lambda *args,**kwargs:None
m.loudness_choice=lambda *args:("OK",None)
m.preview_menu=lambda *args,**kwargs:"1"
# Solo la pregunta de exportación vocal (el autotune ya no existe en V1).
answers=iter(["s"])
old_input=builtins.input
builtins.input=lambda prompt="":next(answers)
try:
    m.stems_mode()
finally:
    builtins.input=old_input
out=m.OUT_ROOT/"Stems"/files[0].stem
export_dir=out/"STEMS_VOCALES_PROCESADOS"
exports=list(export_dir.glob("*_PROCESADO.wav"))
assert len(exports)==6, f"Expected six vocal exports, got {len(exports)}: {[p.name for p in exports]}"
assert (out/"STEMS_MASTER_FINAL.wav").exists(), "Master missing"
assert all(__import__("hashlib").sha256(p.read_bytes()).digest()==original_hashes[p] for p in files), "An original stem changed"
print("PASS MULTI_STEM_CLASSIFICATION_EXPORTS_AND_ORIGINAL_PRESERVATION",len(exports))
print("EXPORTED",sorted(p.name for p in exports))
