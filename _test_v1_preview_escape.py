import builtins, tempfile, wave
from pathlib import Path
import numpy as np
import MixFlowAssistant as m

work=Path(tempfile.mkdtemp(prefix="MixFlowV1_preview_escape_"))
sr=44100
t=np.arange(sr*3)/sr
def make(name,freq):
    p=work/name
    x=0.08*np.sin(2*np.pi*freq*t)
    pcm=np.column_stack([x,x])
    with wave.open(str(p),"wb") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes(np.clip(pcm*32767,-32768,32767).astype("<i2").tobytes())
    return p

mix=make("esc_mix.wav",220)
m.choose_file=lambda title:mix
m.box=lambda *args,**kwargs:None
m.loudness_choice=lambda *args:("OK",None)
m.preview_menu=lambda *args,**kwargs:"esc"
old=builtins.input
builtins.input=lambda prompt="":""
try:
    m.mezcla_mode()
finally:
    builtins.input=old
assert not (m.OUT_ROOT/"Mezcla"/mix.stem/(mix.stem+"_MASTER_FINAL.wav")).exists(),"ESC in MEZCLA preview should not finalize"

voice=make("esc_voice_lead_verse.wav",220)
beat=make("esc_voice_beat.wav",110)
ref=make("esc_voice_alignment_reference.wav",220)
files=[voice,beat,ref]
m.choose_files=lambda title:files
m.box=lambda *args,**kwargs:None
m.loudness_choice=lambda *args:("OK",None)
m.preview_menu=lambda *args,**kwargs:"esc"
old=builtins.input
answers=iter(["n"])
builtins.input=lambda prompt="":next(answers)
try:
    m.stems_mode()
finally:
    builtins.input=old
assert not (m.OUT_ROOT/"Stems"/voice.stem/"STEMS_MASTER_FINAL.wav").exists(),"ESC in STEMS preview should not finalize"
print("PASS ESC_FROM_PENDING_MODES_RETURNS_WITHOUT_FINALIZING")
