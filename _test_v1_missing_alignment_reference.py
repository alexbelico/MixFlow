import builtins, tempfile, wave, hashlib
from pathlib import Path
import numpy as np
import MixFlowAssistant as m

sr=44100
t=np.arange(sr*3)/sr
work=Path(tempfile.mkdtemp(prefix="MixFlowV1_missing_ref_"))
def make(name,freq):
    p=work/name
    x=0.08*np.sin(2*np.pi*freq*t)
    pcm=np.column_stack([x,x]).astype(np.float64)
    with wave.open(str(p),"wb") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes(np.clip(pcm*32767,-32768,32767).astype("<i2").tobytes())
    return p
voice=make("lead_verse.wav",220)
beat=make("instrumental.wav",110)
guide=make("guide.wav",330)
files=[voice,beat,guide]
hashes={p:hashlib.sha256(p.read_bytes()).digest() for p in files}
m.choose_files=lambda title:files
m.box=lambda *args,**kwargs:None
m.loudness_choice=lambda *args:("OK",None)
m.preview_menu=lambda *args,**kwargs:"1"
answers=iter(["8","n","n"])
old=builtins.input
builtins.input=lambda prompt="":next(answers)
try:
    m.stems_mode()
finally:
    builtins.input=old
out=m.OUT_ROOT/"Stems"/files[0].stem/"STEMS_MASTER_FINAL.wav"
assert out.exists(),"Master missing after manual reference assignment"
assert all(hashlib.sha256(p.read_bytes()).digest()==hashes[p] for p in files),"Input was modified"
print("PASS MANUAL_ALIGNMENT_REFERENCE_SELECTION_AND_ORIGINAL_PRESERVATION")
