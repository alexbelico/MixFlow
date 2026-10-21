import builtins, tempfile, wave, hashlib
from pathlib import Path
import numpy as np
import MixFlowAssistant as m

work=Path(tempfile.mkdtemp(prefix="MixFlowV1_stems_undo_"))
sr=44100
t=np.arange(sr*3)/sr
def make(name,freq):
    p=work/name
    x=0.05*np.sin(2*np.pi*freq*t)
    pcm=np.column_stack([x,x])
    with wave.open(str(p),"wb") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes(np.clip(pcm*32767,-32768,32767).astype("<i2").tobytes())
    return p
voice=make("lead_verse.wav",220)
adlibs=make("adlibs_take.wav",440)
beat=make("beat.wav",110)
ref=make("alignment_reference.wav",220)
files=[voice,adlibs,beat,ref]
hashes={p:hashlib.sha256(p.read_bytes()).digest() for p in files}
m.choose_files=lambda title:files
m.box=lambda *args,**kwargs:None
m.loudness_choice=lambda *args:("OK",None)
answers=iter(["n","2","sube volumen voz principal","1","2","sube volumen adlibs","1","3","1","n"])
old=builtins.input
builtins.input=lambda prompt="":next(answers)
try:
    m.stems_mode()
finally:
    builtins.input=old
out=m.OUT_ROOT/"Stems"/files[0].stem
undo=list(out.glob("UNDO_*_mix.wav"))
final=out/"STEMS_MASTER_FINAL.wav"
assert undo,"Undo render missing after two accepted STEMS adjustments"
assert final.exists(),"Final master missing"
assert hashlib.sha256(final.read_bytes()).digest()==hashlib.sha256(undo[-1].read_bytes()).digest(),"Final master differs from restored STEMS state"
assert all(hashlib.sha256(p.read_bytes()).digest()==hashes[p] for p in files),"An original stem changed"
print("PASS STEMS_MULTI_ACCEPTED_ADJUSTMENTS_UNDO_RESTORES_PREVIOUS_STATE")
