import json, math, os, subprocess, sys
from pathlib import Path
import numpy as np
try:
    from scipy import signal
except Exception:
    signal = None

def _no_window_kwargs():
    if os.name!="nt":
        return {}
    return {"creationflags":getattr(subprocess,"CREATE_NO_WINDOW",0x08000000)}

def run(cmd):
    p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                     encoding="utf-8",errors="replace",**_no_window_kwargs())
    if p.returncode: raise RuntimeError(p.stderr[-4000:])
    return p.stdout

def probe(path):
    return json.loads(run(["ffprobe","-v","error","-show_format","-show_streams","-of","json",str(path)]))

def loudnorm(path):
    p=subprocess.run(["ffmpeg","-hide_banner","-nostats","-i",str(path),
                      "-af","loudnorm=I=-10:TP=-1:LRA=11:print_format=json","-f","null","-"],
                     stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                     encoding="utf-8",errors="replace",**_no_window_kwargs())
    if p.returncode: raise RuntimeError(p.stderr[-4000:])
    s=p.stderr; a=s.rfind("{"); b=s.rfind("}")
    if a<0 or b<=a: raise RuntimeError("No se encontro JSON de loudnorm")
    return json.loads(s[a:b+1])

def decode_channels(path, sr, ch):
    p=subprocess.run(["ffmpeg","-v","error","-i",str(path),"-ar",str(sr),"-ac",str(ch),
                      "-f","f32le","-acodec","pcm_f32le","pipe:1"],
                     stdout=subprocess.PIPE,stderr=subprocess.PIPE,**_no_window_kwargs())
    if p.returncode: raise RuntimeError(p.stderr.decode(errors="replace"))
    x=np.frombuffer(p.stdout,dtype="<f4")
    n=len(x)-(len(x)%ch)
    return x[:n].reshape(-1,ch)

def decode(path, sr, ch):
    return decode_channels(path, sr, ch).mean(axis=1)

def signal_diagnostics(channels, sr):
    """Technical diagnostics; silence is a low-level interval, not a musical-section label."""
    frames=len(channels)
    peak=float(np.max(np.abs(channels))) if frames else 0.0
    clipped=float(np.mean(np.abs(channels)>=0.999)) if frames else 0.0
    result={"near_full_scale_sample_ratio":clipped,"near_full_scale_sample_count":int(np.sum(np.abs(channels)>=0.999))}
    if channels.shape[1]>=2 and frames:
        left=channels[:,0].astype(np.float64); right=channels[:,1].astype(np.float64)
        lr=np.sqrt(np.mean(left*left)); rr=np.sqrt(np.mean(right*right))
        corr=float(np.corrcoef(left,right)[0,1]) if np.std(left)>1e-12 and np.std(right)>1e-12 else 0.0
        mid=(left+right)*0.5; side=(left-right)*0.5
        mid_rms=float(np.sqrt(np.mean(mid*mid))); side_rms=float(np.sqrt(np.mean(side*side)))
        result["stereo"]={
            "lr_correlation":corr,
            "left_rms_dbfs":20*math.log10(max(float(lr),1e-12)),
            "right_rms_dbfs":20*math.log10(max(float(rr),1e-12)),
            "left_right_rms_difference_db":20*math.log10(max(float(lr),1e-12))-20*math.log10(max(float(rr),1e-12)),
            "side_to_mid_db":20*math.log10(max(side_rms,1e-12)/max(mid_rms,1e-12))
        }
    # Short windows allow silence/quiet intervals to be found without claiming musical structure.
    win=max(1,int(sr*0.25))
    quiet=[]
    for start in range(0,frames,win):
        block=channels[start:min(start+win,frames)]
        rms=float(np.sqrt(np.mean(block.astype(np.float64)**2))) if len(block) else 0.0
        quiet.append(rms<10**(-55/20))
    regions=[]; start_idx=None
    for i,is_quiet in enumerate(quiet+[False]):
        if is_quiet and start_idx is None: start_idx=i
        elif not is_quiet and start_idx is not None:
            end_idx=i
            if (end_idx-start_idx)*0.25>=0.5:
                regions.append({"start_s":round(start_idx*0.25,2),"end_s":round(min(end_idx*0.25,frames/sr),2),
                                "duration_s":round((end_idx-start_idx)*0.25,2)})
            start_idx=None
    result["quiet_regions_below_minus55dbfs_min_0_5s"]=regions[:100]
    # Three-second RMS distribution gives a coarse dynamics profile over time.
    dyn_win=max(1,int(sr*3.0)); dyn=[]
    for start in range(0,frames,dyn_win):
        block=channels[start:min(start+dyn_win,frames)]
        if len(block):
            dyn.append(20*math.log10(max(float(np.sqrt(np.mean(block.astype(np.float64)**2))),1e-12)))
    if dyn:
        transitions=[]
        for i in range(1,len(dyn)):
            delta=float(dyn[i]-dyn[i-1])
            if abs(delta)>=6.0:
                transitions.append({"time_s":round(i*3.0,2),"from_dbfs":round(float(dyn[i-1]),2),
                                    "to_dbfs":round(float(dyn[i]),2),"change_db":round(delta,2)})
        result["windowed_rms_dbfs_3s"]={
            "minimum":round(float(np.min(dyn)),2),"p10":round(float(np.percentile(dyn,10)),2),
            "median":round(float(np.median(dyn)),2),"p90":round(float(np.percentile(dyn,90)),2),
            "maximum":round(float(np.max(dyn)),2),"windows":len(dyn),
            "candidate_energy_transitions":transitions[:100]}
    return result

def spectrum(x,sr):
    if signal:
        f,p=signal.welch(x,fs=sr,nperseg=min(65536,len(x)))
    else:
        n=min(len(x),262144); w=np.hanning(n); f=np.fft.rfftfreq(n,1/sr); p=np.abs(np.fft.rfft(x[-n:]*w))**2
    total=np.sum(p[(f>=20)&(f<=min(20000,sr/2))])+1e-20
    bands={"sub_20_60":(20,60),"bass_60_150":(60,150),"lowmid_150_350":(150,350),
           "mid_350_2k":(350,2000),"presence_2k_5k":(2000,5000),
           "high_5k_8k":(5000,8000),"air_8k_16k":(8000,16000)}
    return {k:float(np.sum(p[(f>=lo)&(f<min(hi,sr/2))])/total) for k,(lo,hi) in bands.items()}

def analyze(path):
    info=probe(path)
    st=next(s for s in info["streams"] if s.get("codec_type")=="audio")
    sr=int(st["sample_rate"]); ch=int(st.get("channels",1))
    channels=decode_channels(path,sr,ch)
    x=channels.mean(axis=1) if len(channels) else np.zeros(0,dtype=np.float32)
    peak=float(np.max(np.abs(x))) if len(x) else 0.0
    rms=float(np.sqrt(np.mean(x*x))) if len(x) else 0.0
    crest=float(peak/rms) if rms else 0.0
    dc=float(np.mean(x)) if len(x) else 0.0
    diagnostics=signal_diagnostics(channels,sr)
    lm=loudnorm(path)
    return {"file":str(path),"format":{"sample_rate":sr,"channels":ch,"codec":st.get("codec_name"),
            "duration":float(info.get("format",{}).get("duration",0))},
            "loudness":lm,"rms_linear":rms,"peak_linear":peak,
            "peak_dbfs":20*math.log10(max(peak,1e-12)),
            "rms_dbfs":20*math.log10(max(rms,1e-12)),
            "crest_factor_db":20*math.log10(max(crest,1e-12)),
            "dc_offset":dc,"spectrum":spectrum(x,sr),"diagnostics":diagnostics}

def main():
    if len(sys.argv)!=2:
        print('Uso: Analizar_Mezcla.bat "mezcla.wav"'); return 1
    src=Path(sys.argv[1]).resolve()
    result=analyze(src)
    report=src.parent/(src.stem+"_mixflow_analysis.json")
    report.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))
    print("REPORT:",report)
    return 0

if __name__=="__main__": raise SystemExit(main())
