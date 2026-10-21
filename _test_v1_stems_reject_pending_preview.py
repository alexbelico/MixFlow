import builtins, subprocess, tempfile, hashlib
from pathlib import Path
import MixFlowAssistant as m

work=Path(tempfile.mkdtemp(prefix="MixFlowV1_stems_reject_"))
def make(name,expr):
    p=work/name
    subprocess.run(["ffmpeg","-y","-hide_banner","-loglevel","error","-f","lavfi","-i",f"aevalsrc={expr}:s=44100:d=3","-c:a","pcm_s24le",str(p)],check=True)
    return p
voice=make("voz_principal_versos.wav","0.08*sin(2*PI*220*t)")
beat=make("beat.wav","0.08*sin(2*PI*100*t)+0.04*sin(2*PI*400*t)")
ref=make("alignment_reference.wav","0.08*sin(2*PI*220*t)+0.08*sin(2*PI*100*t)")
files=[voice,beat,ref]
m.choose_files=lambda title:files
m.box=lambda *args,**kwargs:None
m.loudness_choice=lambda:("OK",None)
answers=iter(["n","2","sube volumen voz principal","2","1","n"])
old_input=builtins.input
builtins.input=lambda prompt="":next(answers)
try:
    m.stems_mode()
finally:
    builtins.input=old_input
out=m.OUT_ROOT/"Stems"/files[0].stem
rejected=list(out.glob("REJECT_*_mix.wav"))
final=out/"STEMS_MASTER_FINAL.wav"
assert rejected, "Rejected pending STEMS preview was not rebuilt"
assert final.exists(), "Final master missing"
assert hashlib.sha256(final.read_bytes()).digest()==hashlib.sha256(rejected[-1].read_bytes()).digest(), "Final master is not byte-identical to restored accepted state"
print("PASS STEMS_REJECTED_PREVIEW_REVERTS_TO_ACCEPTED_STATE")
