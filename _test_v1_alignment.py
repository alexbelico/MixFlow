import subprocess, tempfile
from pathlib import Path
import numpy as np
import soundfile as sf
import MixFlowAssistant as m

work=Path(tempfile.mkdtemp(prefix='MixFlowV1_alignment_'))
sr=2000; dur=8; n=sr*dur
rng=np.random.default_rng(1234)
env=np.repeat(rng.choice([0.0,0.1,0.35],size=dur*50,p=[0.55,0.25,0.20]),sr//50)[:n]
t=np.arange(n)/sr
base=(env*np.sin(2*np.pi*220*t)).astype(np.float32)
d=sr//2
# Reference begins 0.5 s later than source: the source needs a +0.5 s delay.
ref_early=np.concatenate([np.zeros(d,dtype=np.float32),base[:-d]])
src_early=base
sf.write(work/'ref_late.wav',ref_early,sr); sf.write(work/'src_early.wav',src_early,sr)
off,sc=m.estimate_alignment_offset(work/'ref_late.wav',work/'src_early.wav',max_seconds=8)
assert 0.35 <= off <= 0.65, f'Expected positive delay near +0.5s, got {off:.3f}s'
assert sc>=0.20, f'Expected usable score, got {sc:.3f}'
# Source begins 0.5 s later than reference: the source needs trimming (negative correction).
ref_early2=base
src_late=np.concatenate([np.zeros(d,dtype=np.float32),base[:-d]])
sf.write(work/'ref_early.wav',ref_early2,sr); sf.write(work/'src_late.wav',src_late,sr)
off2,sc2=m.estimate_alignment_offset(work/'ref_early.wav',work/'src_late.wav',max_seconds=8)
assert -0.65 <= off2 <= -0.35, f'Expected negative trim near -0.5s, got {off2:.3f}s'
# Different steady tones have no envelope landmarks and must not trigger a fabricated offset.
steady_ref=(0.2*np.sin(2*np.pi*220*t)).astype(np.float32)
steady_src=(0.2*np.sin(2*np.pi*330*t)).astype(np.float32)
sf.write(work/'steady_ref.wav',steady_ref,sr); sf.write(work/'steady_src.wav',steady_src,sr)
off3,_=m.estimate_alignment_offset(work/'steady_ref.wav',work/'steady_src.wav',max_seconds=8)
assert abs(off3)<0.02, f'Ambiguous steady tones should remain unchanged, got {off3:.3f}s'
short_t=np.arange(int(sr*0.2))/sr
sf.write(work/'short_ref.wav',(0.2*np.sin(2*np.pi*220*short_t)).astype(np.float32),sr)
sf.write(work/'short_src.wav',(0.2*np.sin(2*np.pi*330*short_t)).astype(np.float32),sr)
off4,_=m.estimate_alignment_offset(work/'short_ref.wav',work/'short_src.wav',max_seconds=8)
assert abs(off4)<0.02, f'Short ambiguous files should remain unchanged, got {off4:.3f}s'
print(f'PASS ALIGN_SHORT_FILES_SAFE_NO_OFFSET offset={off4:+.3f}s')
print(f'PASS ALIGN_AMBIGUOUS_STEADY_ENVELOPES offset={off3:+.3f}s')
print(f'PASS ALIGN_SOURCE_EARLY correction={off:+.3f}s score={sc:.2f}')
print(f'PASS ALIGN_SOURCE_LATE correction={off2:+.3f}s score={sc2:.2f}')
