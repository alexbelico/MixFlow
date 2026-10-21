import json, math, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
try:
    from scipy import signal
except Exception:
    signal = None
TARGET_I, TARGET_TP, TARGET_LRA = -10.0, -1.0, 11.0

def run(cmd):
    p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace')
    if p.returncode: raise RuntimeError(p.stderr[-5000:])
    return p.stdout

def probe(p):
    return json.loads(run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(p)]))

def loudnorm(p):
    cmd=['ffmpeg','-hide_banner','-nostats','-i',str(p),'-af',f'loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}:print_format=json','-f','null','-']
    q=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace')
    if q.returncode: raise RuntimeError(q.stderr[-5000:])
    s=q.stderr; a=s.rfind('{'); b=s.rfind('}')
    if a<0 or b<=a: raise RuntimeError('No se encontro JSON de loudnorm')
    return json.loads(s[a:b+1])

def decode(p):
    i=probe(p); st=next(s for s in i['streams'] if s.get('codec_type')=='audio')
    sr=int(st['sample_rate']); ch=int(st.get('channels',1))
    q=subprocess.run(['ffmpeg','-v','error','-i',str(p),'-f','f32le','-acodec','pcm_f32le','pipe:1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if q.returncode: raise RuntimeError(q.stderr.decode(errors='replace'))
    x=np.frombuffer(q.stdout,dtype='<f4')
    x=x[:len(x)-(len(x)%ch)].reshape(-1,ch) if ch>1 else x
    return sr,x.mean(axis=1)

def spectrum(x,sr):
    if signal:
        f,p=signal.welch(x,fs=sr,nperseg=min(65536,len(x)))
    else:
        n=min(len(x),262144); w=np.hanning(n); f=np.fft.rfftfreq(n,1/sr); p=np.abs(np.fft.rfft(x[-n:]*w))**2
    total=np.sum(p[(f>=20)&(f<=min(20000,sr/2))])+1e-20
    bands={'bass_60_150':(60,150),'lowmid_150_350':(150,350),'presence_2k_5k':(2000,5000),'air_8k_16k':(8000,16000)}
    return {k:float(np.sum(p[(f>=lo)&(f<min(hi,sr/2))])/total) for k,(lo,hi) in bands.items()}

def recipe(l, e):
    fs=['highpass=f=28:p=2']
    if e['bass_60_150']>.30: fs+=['equalizer=f=95:t=q:w=1:g=-1.2']
    elif e['bass_60_150']>.25: fs+=['equalizer=f=95:t=q:w=1:g=-0.7']
    if e['lowmid_150_350']>.28: fs+=['equalizer=f=240:t=q:w=1:g=-0.8']
    elif e['lowmid_150_350']>.24: fs+=['equalizer=f=240:t=q:w=1:g=-0.4']
    if e['presence_2k_5k']<.16: fs+=['equalizer=f=2800:t=q:w=1:g=0.7']
    elif e['presence_2k_5k']>.27: fs+=['equalizer=f=3000:t=q:w=1:g=-0.5']
    if e['air_8k_16k']<.07: fs+=['equalizer=f=10000:t=q:w=.9:g=.5']
    elif e['air_8k_16k']>.18: fs+=['equalizer=f=10000:t=q:w=.9:g=-0.3']
    lra=float(l.get('input_lra',0))
    fs+=['acompressor=threshold=-18dB:ratio=1.35:attack=20:release=180:makeup=0.5' if lra>8 else 'acompressor=threshold=-16dB:ratio=1.2:attack=25:release=220:makeup=0']
    fs+=['alimiter=limit=0.89125:attack=5:release=80:level=1']
    return fs

def main():
    if len(sys.argv)!=2: print('Uso: MASTER.bat "mezcla.wav"'); return 1
    src=Path(sys.argv[1]).resolve(); out=src.parent/'MASTER_OUTPUT'; out.mkdir(exist_ok=True)
    master=out/f'{src.stem}_MASTER_32FLOAT.wav'; report=out/f'{src.stem}_analysis.json'
    print('[1/6] Inspeccion tecnica'); info=probe(src); st=next(s for s in info['streams'] if s.get('codec_type')=='audio')
    print(st.get('sample_rate'),'Hz |',st.get('channels'),'ch |',st.get('codec_name'))
    print('[2/6] LUFS / True Peak / LRA'); lm=loudnorm(src); print(lm)
    print('[3/6] Espectro'); sr,x=decode(src); en=spectrum(x,sr); print(en)
    print('[4/6] Receta adaptativa'); fs=recipe(lm,en); print(' , '.join(fs))
    with tempfile.TemporaryDirectory() as td:
        mid=Path(td)/'mid.wav'; af=','.join(fs)
        run(['ffmpeg','-y','-hide_banner','-i',str(src),'-af',af,'-ar','44100','-c:a','pcm_f32le',str(mid)])
        m=loudnorm(mid)
        lf=(f'loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}:'
            f'measured_I={m["input_i"]}:measured_TP={m["input_tp"]}:'
            f'measured_LRA={m["input_lra"]}:measured_thresh={m["input_thresh"]}:'
            f'offset={m["target_offset"]}:linear=true:print_format=summary')
        print('[5/6] Master 32-bit float'); run(['ffmpeg','-y','-hide_banner','-i',str(mid),'-af',lf,'-ar','44100','-c:a','pcm_f32le',str(master)])
    print('[6/6] Verificacion final'); final=loudnorm(master); print(final)
    report.write_text(json.dumps({'source':str(src),'output':str(master),'target':{'LUFS_I':TARGET_I,'TP_dBTP':TARGET_TP,'LRA':TARGET_LRA},'source_loudness':lm,'spectrum':en,'filters':fs,'final_loudness':final},indent=2),encoding='utf-8')
    print('\nMASTER:',master); print('REPORT:',report); return 0
if __name__=='__main__': raise SystemExit(main())