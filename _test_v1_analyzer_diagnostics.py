import tempfile, wave
from pathlib import Path
import numpy as np
from MixFlowAnalyzer import analyze

sr=44100
n_sil=sr
n_low=sr*2
n_high=sr*4
t_low=np.arange(n_low)/sr
t_high=np.arange(n_high)/sr
left=np.concatenate([np.zeros(n_sil),0.02*np.sin(2*np.pi*440*t_low),0.2*np.sin(2*np.pi*440*t_high)])
right=np.concatenate([np.zeros(n_sil),-0.01*np.sin(2*np.pi*440*t_low),-0.1*np.sin(2*np.pi*440*t_high)])
stereo=np.column_stack([left,right])
pcm=np.clip(stereo*32767,-32768,32767).astype("<i2")
path=Path(tempfile.mkdtemp(prefix="MixFlowAnalyzer_diag_"))/"stereo_diag.wav"
with wave.open(str(path),"wb") as wf:
    wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sr); wf.writeframes(pcm.tobytes())
a=analyze(path)
d=a["diagnostics"]
assert d["stereo"]["lr_correlation"] < -0.98, d["stereo"]
assert abs(d["stereo"]["left_right_rms_difference_db"]-6.02)<0.15, d["stereo"]
assert d["near_full_scale_sample_count"] == 0, d["near_full_scale_sample_count"]
assert d["quiet_regions_below_minus55dbfs_min_0_5s"], "Expected initial silence region"
assert d["windowed_rms_dbfs_3s"]["windows"] >= 1
assert d["windowed_rms_dbfs_3s"]["candidate_energy_transitions"], "Expected a coarse energy-transition candidate"
print("PASS ANALYZER_STEREO_PHASE_CLIPPING_SILENCE_DYNAMICS")
print("correlation",round(d["stereo"]["lr_correlation"],3),"L-R dB",round(d["stereo"]["left_right_rms_difference_db"],2),
      "quiet regions",d["quiet_regions_below_minus55dbfs_min_0_5s"])
