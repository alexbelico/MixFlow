import builtins, subprocess, tempfile
from pathlib import Path
import MixFlowAssistant as m

work=Path(tempfile.mkdtemp(prefix='MixFlowV1_stems_test_'))
def make(name,expr):
    p=work/name
    subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','lavfi','-i',f'aevalsrc={expr}:s=44100:d=3','-c:a','pcm_s24le',str(p)],check=True)
    return p
voice=make('voz_principal_versos.wav','0.08*sin(2*PI*220*t)')
beat=make('beat.wav','0.08*sin(2*PI*100*t)+0.04*sin(2*PI*400*t)')
ref=make('alignment_reference.wav','0.08*sin(2*PI*220*t)+0.08*sin(2*PI*100*t)')
files=[voice,beat,ref]
original_sizes={p:p.stat().st_size for p in files}
m.choose_files=lambda title:files
m.box=lambda *args,**kwargs:None
m.loudness_choice=lambda:('OK',None)
answers=iter(['n','1','n'])
old_input=builtins.input
builtins.input=lambda prompt='':next(answers)
try:
    m.stems_mode()
finally:
    builtins.input=old_input
out=m.OUT_ROOT/'Stems'/files[0].stem/'STEMS_MASTER_FINAL.wav'
assert out.exists(), f'Master not found: {out}'
assert all(p.stat().st_size==original_sizes[p] for p in files), 'An original input was modified'
print('PASS STEMS_FLOW_MASTER_EXISTS',out)
print('PASS STEMS_FLOW_ORIGINALS_UNCHANGED')
