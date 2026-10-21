import json, math, re, subprocess, shutil, copy, os, sys
from pathlib import Path

# Evitar que los menús fallen al imprimir flechas o acentos en consolas Windows cp1252.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
import tkinter as tk
from tkinter import filedialog, ttk

ROOT=Path(__file__).resolve().parent
OUT_ROOT=ROOT.parent/"MixFlow_Output"
OUT_ROOT.mkdir(exist_ok=True)

CATS=[
    "Voz principal — Versos","Segunda voz — Versos",
    "Voz principal — Coros","Segunda voz — Coros",
    "Adlibs","Backs / Remarques","Remarques","Beat","Alignment / Referencia"
]
LOUD={"1":-14.0,"2":-12.0,"3":-10.0,"4":-8.0}

# --- Progress HUD (ventana clara de estado; no cambia el flujo CLI) ---
_PLAY_PROC=None
_HUD=None
_HUD_DISABLED=os.environ.get("MIXFLOW_NO_HUD","").strip() in ("1","true","yes")

class ProgressHud:
    """Ventana siempre encima que muestra etapa/paso sin reemplazar la consola."""
    def __init__(self):
        self.root=None
        self.win=None
        self.var_stage=None
        self.var_step=None
        self.var_detail=None
        self.bar=None
        self.disabled=_HUD_DISABLED

    def ensure(self):
        if self.disabled: return False
        if self.win is not None:
            try:
                if self.win.winfo_exists():
                    return True
            except tk.TclError:
                self.win=None; self.root=None
        try:
            self.root=tk.Tk()
            self.root.withdraw()
            self.win=tk.Toplevel(self.root)
            self.win.title("MixFlow — progreso")
            self.win.geometry("460x160+40+40")
            self.win.attributes("-topmost",True)
            self.win.configure(bg="#1a1d23")
            self.win.resizable(False,False)
            # No cerrar el motor Tk al pulsar la X; solo ocultar.
            self.win.protocol("WM_DELETE_WINDOW",self.win.withdraw)
            frm=tk.Frame(self.win,bg="#1a1d23",padx=16,pady=14)
            frm.pack(fill="both",expand=True)
            tk.Label(frm,text="MIXFLOW",fg="#7dd3fc",bg="#1a1d23",
                     font=("Segoe UI Semibold",11)).pack(anchor="w")
            self.var_stage=tk.StringVar(value="Listo")
            self.var_step=tk.StringVar(value="")
            self.var_detail=tk.StringVar(value="")
            tk.Label(frm,textvariable=self.var_stage,fg="#f8fafc",bg="#1a1d23",
                     font=("Segoe UI",12,"bold"),wraplength=420,justify="left").pack(anchor="w",pady=(8,2))
            tk.Label(frm,textvariable=self.var_step,fg="#94a3b8",bg="#1a1d23",
                     font=("Segoe UI",9)).pack(anchor="w")
            style=ttk.Style(self.root)
            try: style.theme_use("clam")
            except tk.TclError: pass
            style.configure("Mix.Horizontal.TProgressbar",troughcolor="#0f172a",
                            background="#38bdf8",bordercolor="#0f172a",
                            lightcolor="#38bdf8",darkcolor="#0284c7")
            self.bar=ttk.Progressbar(frm,length=420,mode="determinate",style="Mix.Horizontal.TProgressbar")
            self.bar.pack(anchor="w",pady=(10,6))
            tk.Label(frm,textvariable=self.var_detail,fg="#cbd5e1",bg="#1a1d23",
                     font=("Segoe UI",9),wraplength=420,justify="left").pack(anchor="w")
            self.win.deiconify()
            self.root.update_idletasks()
            return True
        except Exception:
            self.disabled=True
            self.root=None; self.win=None
            return False

    def update(self,stage,step=None,total=None,detail=""):
        if not self.ensure(): return
        try:
            self.win.deiconify()
            self.var_stage.set(stage)
            if step is not None and total:
                self.var_step.set(f"Paso {step} de {total}")
                self.bar["maximum"]=max(int(total),1)
                self.bar["value"]=max(0,min(int(step),int(total)))
            elif step is not None:
                self.var_step.set(f"Paso {step}")
            self.var_detail.set((detail or "")[:240])
            self.root.update_idletasks()
            self.root.update()
        except tk.TclError:
            self.win=None; self.root=None

    def close(self):
        if self.root is None and self.win is None: return
        try:
            if self.win is not None: self.win.destroy()
        except tk.TclError: pass
        try:
            if self.root is not None: self.root.destroy()
        except tk.TclError: pass
        self.root=None; self.win=None

def hud():
    global _HUD
    if _HUD is None: _HUD=ProgressHud()
    return _HUD

_PLAY_PATH=None
_PLAY_LABEL=""
_PLAY_VOLUME_DB=0.0
_PLAY_START_S=0.0

def stop_playback():
    global _PLAY_PROC
    if _PLAY_PROC is not None and _PLAY_PROC.poll() is None:
        try: _PLAY_PROC.terminate()
        except OSError: pass
        try: _PLAY_PROC.wait(timeout=2)
        except Exception: pass
    _PLAY_PROC=None

def is_playing():
    return _PLAY_PROC is not None and _PLAY_PROC.poll() is None

def _ffplay_path():
    return shutil.which("ffplay")

def _no_window_kwargs():
    """Evita que FFmpeg/ffplay abran una consola negra en Windows."""
    if os.name!="nt":
        return {}
    flags=getattr(subprocess,"CREATE_NO_WINDOW",0x08000000)
    return {"creationflags":flags}

def _file_rms_db(path,max_seconds=40):
    """RMS aproximado para nivelar A/B (no es LUFS)."""
    try:
        x,sr=audio_mono(path,max_seconds=max_seconds,sr=8000)
        import numpy as np
        rms=float(np.sqrt(np.mean(x*x))) if len(x) else 0.0
        return 20*math.log10(max(rms,1e-12))
    except Exception:
        return None

def play_audio(path,label="",volume_db=0.0,start_s=0.0):
    """Reproduce con ffplay si está disponible; volume_db compensa nivel (A/B).
    start_s salta al tiempo indicado (seek real vía -ss)."""
    global _PLAY_PROC,_PLAY_PATH,_PLAY_LABEL,_PLAY_VOLUME_DB,_PLAY_START_S
    stop_playback()
    path=Path(path)
    if not path.exists():
        print(f"No existe el archivo: {path}")
        return False
    try:
        start_s=max(0.0,float(start_s or 0.0))
    except (TypeError,ValueError):
        start_s=0.0
    _PLAY_PATH=path
    _PLAY_LABEL=label or ""
    _PLAY_VOLUME_DB=float(volume_db or 0.0)
    _PLAY_START_S=start_s
    ff=_ffplay_path()
    if ff:
        if not os.environ.get("MIXFLOW_GUI"):
            print(f"▶ Reproduciendo{' — '+label if label else ''}: {path.name}"
                  + (f" @ {start_s:.2f}s" if start_s>0.05 else ""))
        # -ss antes de -i = seek de entrada (salto real de reproducción)
        cmd=[ff,"-nodisp","-autoexit","-loglevel","error"]
        if start_s>0.02:
            cmd += ["-ss",f"{start_s:.3f}"]
        if abs(float(volume_db))>=0.05:
            amp=10.0**(float(volume_db)/20.0)
            cmd += ["-af",f"volume={amp:.6f}"]
        cmd += ["-i",str(path)]
        _PLAY_PROC=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                                    **_no_window_kwargs())
        return True
    try:
        if os.name=="nt": os.startfile(str(path))
        else: subprocess.Popen(["xdg-open",str(path)],**_no_window_kwargs())
        return True
    except OSError as e:
        print(f"No se pudo reproducir: {e}")
        return False

def seek_playback(start_s,resume=True):
    """Salta a start_s. Si resume=True y había audio, reinicia desde ahí."""
    path=_PLAY_PATH
    if path is None or not Path(path).exists():
        return False
    was=is_playing()
    if resume and (was or start_s is not None):
        return play_audio(path,_PLAY_LABEL,_PLAY_VOLUME_DB,start_s=start_s)
    stop_playback()
    return False

def ab_compare(path_a,path_b,label_a="A (antes)",label_b="B (después)",level_match=True):
    """A/B con loudness/RMS igualado opcional para comparar tono, no volumen."""
    path_a,path_b=Path(path_a),Path(path_b)
    if not path_a.exists() or not path_b.exists():
        print("Faltan archivos para A/B.")
        return
    vol_a=vol_b=0.0
    if level_match:
        ra=_file_rms_db(path_a); rb=_file_rms_db(path_b)
        if ra is not None and rb is not None:
            # Igualar B al nivel de A (y viceversa relativo al más bajo).
            target=(ra+rb)*0.5
            vol_a=target-ra
            vol_b=target-rb
            # Limitar compensación a ±8 dB para no distorsionar.
            vol_a=max(-8.0,min(8.0,vol_a))
            vol_b=max(-8.0,min(8.0,vol_b))
    play_audio(path_a,label_a,volume_db=vol_a)
    if os.environ.get("MIXFLOW_GUI","").strip() in ("1","true","yes"):
        try:
            from tkinter import messagebox
            go=messagebox.askokcancel(
                "A/B nivelado",
                f"Escuchando A — {label_a} (nivel igualado)\n\n"
                f"OK = pasar a B ({label_b})\nCancelar = detener")
        except Exception:
            go=True
        stop_playback()
        if go and path_b.exists():
            play_audio(path_b,label_b,volume_db=vol_b)
        return
    print("\n--- A/B (nivelado) ---")
    ans=input("Enter para escuchar B (o 's'+Enter para saltar)… ").strip().lower()
    stop_playback()
    if ans!="s" and path_b.exists():
        play_audio(path_b,label_b,volume_db=vol_b)

def run(cmd, check=True):
    p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                     encoding="utf-8",errors="replace",**_no_window_kwargs())
    if check and p.returncode:
        raise RuntimeError(p.stderr[-5000:])
    return p

def box(stage,step,total,detail=""):
    # En GUI no tocar la consola (cls abre/parpadea la ventana negra).
    gui=os.environ.get("MIXFLOW_GUI","").strip() in ("1","true","yes")
    if not gui:
        if os.name=="nt":
            os.system("cls")
        else:
            os.system("clear")
        print("="*72)
        print("MIXFLOW ASSISTANT")
        print("[ PROCESO: "+stage+" ]")
        print(f"Paso {step} de {total}")
        if detail: print(detail)
        print("="*72)
    try:
        hud().update(stage,step,total,detail.splitlines()[0] if detail else "")
    except Exception:
        pass

def _dialog_root():
    """Reutiliza el root del HUD si existe para evitar múltiples Tk() en Windows."""
    h=hud()
    if h.root is not None and not h.disabled:
        try:
            if h.root.winfo_exists():
                return h.root,False
        except tk.TclError:
            pass
    root=tk.Tk(); root.withdraw()
    return root,True

def choose_file(title):
    root,owned=_dialog_root()
    try:
        root.attributes("-topmost",True)
        p=filedialog.askopenfilename(parent=root,title=title,
            filetypes=[("WAV","*.wav"),("Audio","*.wav *.flac *.mp3"),("Todos","*.*")])
    finally:
        if owned:
            try: root.destroy()
            except tk.TclError: pass
    return Path(p) if p else None

def choose_files(title):
    root,owned=_dialog_root()
    try:
        root.attributes("-topmost",True)
        ps=filedialog.askopenfilenames(parent=root,title=title,
            filetypes=[("WAV","*.wav"),("Audio","*.wav *.flac *.mp3"),("Todos","*.*")])
    finally:
        if owned:
            try: root.destroy()
            except tk.TclError: pass
    return [Path(p) for p in ps]

def probe(p):
    return json.loads(run(["ffprobe","-v","error","-show_format","-show_streams","-of","json",str(p)]).stdout)

def loudnorm(p,target=-10):
    r=run(["ffmpeg","-hide_banner","-nostats","-i",str(p),"-af",f"loudnorm=I={target}:TP=-1:LRA=11:print_format=json","-f","null","-"])
    s=r.stderr; a=s.rfind("{"); b=s.rfind("}")
    if a<0 or b<0: return {}
    try: return json.loads(s[a:b+1])
    except Exception: return {}

_ANALYZE_CACHE={}

def analyze_basic(p):
    # Reuse the project analyzer; cache por path+mtime+size para no reprocesar.
    try: hud().update("Analizando audio…",detail=Path(p).name)
    except Exception: pass
    p=Path(p)
    try:
        st=p.stat()
        key=(str(p.resolve()),st.st_mtime_ns,st.st_size)
    except OSError:
        key=None
    if key and key in _ANALYZE_CACHE:
        return copy.deepcopy(_ANALYZE_CACHE[key])
    from MixFlowAnalyzer import analyze as detailed_analyze
    result=detailed_analyze(p)
    fmt=result["format"]
    out={
        "sr":int(fmt["sample_rate"]),
        "channels":int(fmt["channels"]),
        "duration":float(fmt["duration"]),
        "peak_dbfs":float(result["peak_dbfs"]),
        "rms_dbfs":float(result["rms_dbfs"]),
        "loudness":result["loudness"],
        "spectrum":result["spectrum"],
        "crest_factor_db":float(result["crest_factor_db"]),
        "dc_offset":float(result["dc_offset"]),
        "diagnostics":result.get("diagnostics",{}),
        "codec":fmt.get("codec")
    }
    if key:
        _ANALYZE_CACHE[key]=copy.deepcopy(out)
        # Evitar crecimiento ilimitado
        if len(_ANALYZE_CACHE)>24:
            _ANALYZE_CACHE.pop(next(iter(_ANALYZE_CACHE)))
    return out

def audio_mono(p,max_seconds=90,sr=4000):
    r=subprocess.run(["ffmpeg","-v","error","-i",str(p),"-ar",str(sr),"-ac","1","-t",str(max_seconds),
                      "-f","f32le","-acodec","pcm_f32le","pipe:1"],
                     stdout=subprocess.PIPE,stderr=subprocess.PIPE,**_no_window_kwargs())
    if r.returncode: raise RuntimeError(r.stderr.decode(errors="replace"))
    import numpy as np
    return np.frombuffer(r.stdout,dtype="<f4"),sr

def classify(p):
    n=p.stem.lower().replace("_"," ").replace("-"," ")
    if any(k in n for k in ["alignment","referencia","reference","ref "]): return "Alignment / Referencia"
    if "adlib" in n or "ad libs" in n: return "Adlibs"
    # Remarques vs Backs
    if any(k in n for k in ["remarque","remarques","remate","remates"]) and "back" not in n:
        return "Remarques"
    if any(k in n for k in ["back","backs","background"]): return "Backs / Remarques"
    if "beat" in n or "instrumental" in n or "music" in n: return "Beat"
    cor=("coro" in n or "chorus" in n)
    sec=any(k in n for k in ["segunda","2da","second"])
    pri=any(k in n for k in ["principal","main","lead","voz 1","voz1"])
    if cor and sec: return "Segunda voz — Coros"
    if cor and (pri or "voz" in n): return "Voz principal — Coros"
    if not cor and sec: return "Segunda voz — Versos"
    if not cor and (pri or "voz" in n): return "Voz principal — Versos"
    return None

def ask_classification(files):
    out={}
    for p in files:
        c=classify(p)
        if c is None:
            print(f"\nNo pude clasificar: {p.name}")
            for i,x in enumerate(CATS,1): print(f"{i}. {x}")
            while True:
                v=input("Elige categoría: ").strip()
                if v.isdigit() and 1<=int(v)<=len(CATS):
                    c=CATS[int(v)-1]; break
        out[p]=c
    return out

def estimate_alignment_offset(ref,src,max_seconds=30):
    """Return (offset_s, score). Positive delays an early stem; negative trims a late stem."""
    import numpy as np
    a,sr=audio_mono(ref,max_seconds,2000); b,_=audio_mono(src,max_seconds,2000)
    if len(a)<1000 or len(b)<1000: return 0.0,0.0
    n=min(len(a),len(b),sr*max_seconds)
    frame=max(20,int(sr*0.02))  # 20 ms RMS envelope
    n=(n//frame)*frame
    if n<frame*30: return 0.0,0.0
    a=a[:n].reshape(-1,frame)
    b=b[:n].reshape(-1,frame)
    a=np.sqrt(np.mean(a*a,axis=1)); b=np.sqrt(np.mean(b*b,axis=1))
    if (np.std(a)<max(float(np.mean(a))*0.02,1e-5) or
        np.std(b)<max(float(np.mean(b))*0.02,1e-5)):
        return 0.0,0.0
    a=a-a.mean(); b=b-b.mean()
    na=np.linalg.norm(a); nb=np.linalg.norm(b)
    if na<1e-8 or nb<1e-8: return 0.0,0.0
    a/=na; b/=nb
    env_sr=sr/frame
    lagmax=min(int(env_sr*3),len(a)//3)
    best=(0,-1.0)
    for lag in range(-lagmax,lagmax+1):
        if lag>=0:
            aa=a[lag:]; bb=b[:len(aa)]
        else:
            bb=b[-lag:]; aa=a[:len(bb)]
        if len(aa)<30: continue
        score=float(np.dot(aa,bb)/max(np.linalg.norm(aa)*np.linalg.norm(bb),1e-12))
        if score>best[1]: best=(lag,score)
    if best[1] < 0.20: return 0.0,float(best[1])
    return best[0]/env_sr,float(best[1])

def align_stems(classified,ref,outdir,manual_offsets=None):
    """Alinea stems a la referencia.

    Si el score es bajo (<0.20) y no hay offset manual, marca needs_manual=True
    y NO asume 0 (deja copia sin desplazar hasta que el usuario confirme).
    manual_offsets: dict path→offset_s (positivo = retrasar stem).
    """
    outdir.mkdir(parents=True,exist_ok=True)
    manual_offsets=manual_offsets or {}
    aligned={}
    reports={}
    for p,c in classified.items():
        if c=="Alignment / Referencia": continue
        dest=outdir/(p.stem+"_ALIGNED.wav")
        needs_manual=False
        if p in manual_offsets:
            off=float(manual_offsets[p]); score=1.0
        else:
            off,score=estimate_alignment_offset(ref,p)
            if score < 0.20:
                needs_manual=True
                off=0.0  # no inventar; UI pedirá ms manuales
        gui=os.environ.get("MIXFLOW_GUI","").strip() in ("1","true","yes")
        if not gui:
            print(f"  {c}: {p.name} | offset {off:+.3f}s ({off*1000:+.0f} ms) | score {score:.2f}"
                  + (" | NEEDS_MANUAL" if needs_manual else ""))
        reports[p]={"offset_s":off,"offset_ms":off*1000,"score":score,
                    "category":c,"needs_manual":needs_manual}
        if abs(off)<0.001:
            shutil.copy2(p,dest)
        elif off>0:
            ms=int(round(off*1000))
            run(["ffmpeg","-y","-hide_banner","-loglevel","error","-i",str(p),"-af",f"adelay={ms}:all=1",
                 "-c:a","pcm_f32le",str(dest)])
        else:
            sec=max(0,-off)
            run(["ffmpeg","-y","-hide_banner","-loglevel","error","-ss",f"{sec:.4f}","-i",str(p),
                 "-c:a","pcm_f32le",str(dest)])
        aligned[p]=dest
    align_stems.last_reports=reports
    return aligned

def _hz_to_midi(hz):
    return 69.0+12.0*math.log2(max(hz,1.0)/440.0)

def _midi_to_hz(midi):
    return 440.0*(2.0**((midi-69.0)/12.0))

def _detect_frame_pitch_hz(frame,sr,fmin=70.0,fmax=1000.0):
    """Autocorrelación simple por frame → Hz fundamental o None."""
    import numpy as np
    if len(frame)<64: return None
    x=frame.astype(np.float64)
    x=x-x.mean()
    if np.sqrt(np.mean(x*x))<1e-4: return None
    corr=np.correlate(x,x,mode="full")[len(x)-1:]
    i0=max(1,int(sr/fmax)); i1=min(len(corr)-1,int(sr/fmin))
    if i1<=i0: return None
    seg=corr[i0:i1]
    lag=int(np.argmax(seg))+i0
    if corr[lag]<0.3*corr[0]: return None
    return sr/float(lag)

def segment_notes(path,sr_target=22050,hop_ms=40,min_note_ms=90,max_note_s=2.5):
    """Segmenta notas por estabilidad de pitch (no bloques fijos de 20 s)."""
    import numpy as np
    x,sr=audio_mono(path,max_seconds=600,sr=sr_target)
    hop=max(64,int(sr*hop_ms/1000))
    win=hop*2
    times=[]; hz_list=[]
    for i in range(0,max(1,len(x)-win),hop):
        hz=_detect_frame_pitch_hz(x[i:i+win],sr)
        times.append(i/sr); hz_list.append(hz)
    notes=[]
    i=0
    while i<len(hz_list):
        if hz_list[i] is None:
            i+=1; continue
        j=i
        ref=hz_list[i]
        while j<len(hz_list) and hz_list[j] is not None:
            # Misma nota si está dentro de ~50 cents.
            if abs(1200*math.log2(hz_list[j]/ref))>50:
                break
            # Actualizar ref suavemente
            ref=0.85*ref+0.15*hz_list[j]
            j+=1
            if (times[min(j,len(times)-1)]-times[i])>=max_note_s:
                break
        dur=times[min(j,len(times)-1)]-times[i]
        if dur*1000>=min_note_ms:
            median_hz=float(np.median([h for h in hz_list[i:j] if h]))
            notes.append({"start":times[i],"end":times[i]+dur,"hz":median_hz,
                          "midi":_hz_to_midi(median_hz)})
        i=max(j,i+1)
    return notes,sr

def _ffmpeg_has_rubberband():
    try:
        r=run(["ffmpeg","-hide_banner","-filters"],check=False)
        return "rubberband" in (r.stdout or "")+ (r.stderr or "")
    except Exception:
        return False

def tune_stem_note_by_note(src,out,intensity=0.7,preserve_formants=True):
    """Afinación nota a nota (no tramos largos). Excluye no-voz. Sin ganancia automática.

    - Solo corrige segmentos con pitch detectado (voz).
    - Prefer rubberband+formants si FFmpeg lo trae; si no, asetrate/atempo.
    - Crossfade corto entre segmentos al reensamblar.
    """
    src,out=Path(src),Path(out)
    intensity=max(0.0,min(1.0,float(intensity)))
    notes,_=segment_notes(src)
    # Filtrar notas demasiado largas (ruido / no-voz sostenido)
    notes=[n for n in notes if (n["end"]-n["start"])<=2.5 and (n["end"]-n["start"])>=0.09]
    if not notes or intensity<0.05:
        shutil.copy2(src,out)
        return {"notes":0,"path":str(out),"formants":False}
    work=out.parent/(out.stem+"_tunework")
    work.mkdir(exist_ok=True)
    segs=[]
    dur=float(probe(src).get("format",{}).get("duration") or 0)
    cursor=0.0
    idx=0
    use_rb=_ffmpeg_has_rubberband() if preserve_formants else False
    xfade=0.008  # 8 ms crossfade
    for n in notes:
        if n["start"]>cursor+0.01:
            raw=work/f"raw_{idx:03d}.wav"
            run(["ffmpeg","-y","-hide_banner","-loglevel","error","-ss",f"{cursor:.4f}",
                 "-t",f"{n['start']-cursor:.4f}","-i",str(src),"-c:a","pcm_f32le",str(raw)])
            segs.append(raw); idx+=1
        target_midi=round(n["midi"])
        delta=(target_midi-n["midi"])*intensity
        ratio=2.0**(delta/12.0)
        note=work/f"note_{idx:03d}.wav"
        if use_rb and abs(delta)>0.02:
            # pitch en semitonos; formant preservado
            af=f"rubberband=pitch={delta:.4f}:pitchq=quality:formant=preserved"
        else:
            af=f"asetrate=44100*{ratio:.8f},aresample=44100,atempo={max(0.5,min(2.0,1.0/ratio)):.8f}"
        try:
            run(["ffmpeg","-y","-hide_banner","-loglevel","error","-ss",f"{n['start']:.4f}",
                 "-t",f"{max(0.01,n['end']-n['start']):.4f}","-i",str(src),"-af",af,
                 "-c:a","pcm_f32le",str(note)])
        except RuntimeError:
            run(["ffmpeg","-y","-hide_banner","-loglevel","error","-ss",f"{n['start']:.4f}",
                 "-t",f"{max(0.01,n['end']-n['start']):.4f}","-i",str(src),
                 "-c:a","pcm_f32le",str(note)])
        segs.append(note); idx+=1
        cursor=n["end"]
    if cursor<dur-0.01:
        raw=work/f"raw_{idx:03d}.wav"
        run(["ffmpeg","-y","-hide_banner","-loglevel","error","-ss",f"{cursor:.4f}",
             "-i",str(src),"-c:a","pcm_f32le",str(raw)])
        segs.append(raw)
    if not segs:
        shutil.copy2(src,out); return {"notes":0,"path":str(out),"formants":use_rb}
    # Reensamblar con acrossfade si hay ≥2 segmentos
    if len(segs)==1:
        shutil.copy2(segs[0],out)
    elif len(segs)<=8:
        # acrossfade chain (limitado a pocos inputs)
        inputs=[]; filters=[]; prev="0:a"
        for i,s in enumerate(segs):
            inputs+=["-i",str(s)]
        cur=f"[0:a]"
        last=None
        for i in range(1,len(segs)):
            out_l=f"[x{i}]"
            filters.append(f"{cur}[{i}:a]acrossfade=d={xfade:.3f}:c1=tri:c2=tri{out_l}")
            cur=out_l; last=out_l
        run(["ffmpeg","-y","-hide_banner","-loglevel","error",*inputs,
             "-filter_complex",";".join(filters),"-map",last,"-c:a","pcm_f32le",str(out)])
    else:
        lst=work/"list.txt"
        lst.write_text("".join(f"file '{s.resolve().as_posix()}'\n" for s in segs),encoding="utf-8")
        run(["ffmpeg","-y","-hide_banner","-loglevel","error","-f","concat","-safe","0","-i",str(lst),
             "-c:a","pcm_f32le",str(out)])
    return {"notes":len(notes),"path":str(out),"intensity":intensity,"formants":use_rb}

def stem_recipe(cat,analysis,settings):
    """Cadena por stem. Sin ganancia ni compresión automática oculta por defecto.

    Solo EQ base muy ligero + ajustes explícitos del usuario (bright/body/comp_ratio/gain).
    """
    if cat=="Beat":
        return []
    fs=[]
    # Highpass técnico mínimo solo en voces (no es “procesamiento creativo”).
    if "Voz" in cat or cat in ("Adlibs","Backs / Remarques","Remarques"):
        fs.append("highpass=f=45")
        if "Coros" in cat and settings.get("bright") is None and not settings.get("no_default_eq"):
            pass  # sin EQ automático de brillo
        if settings.get("unique"):
            fs.append("equalizer=f=2500:t=q:w=1:g=-0.25")
        if settings.get("bright",0):
            fs.append(f"equalizer=f=3500:t=q:w=1:g={settings['bright']:.2f}")
        if settings.get("body",0):
            fs.append(f"equalizer=f=180:t=q:w=1:g={settings['body']:.2f}")
        # Compresión SOLO si el usuario la pidió explícitamente.
        if settings.get("comp_ratio"):
            fs.append(f"acompressor=threshold=-18dB:ratio={settings['comp_ratio']:.2f}:attack=18:release=160:makeup=1")
    return fs

def render_state(sources,classified,settings,outdir,label,sample_rate=44100,progress=None):
    """Renderiza stems. sample_rate preserva el de la fuente (p.ej. 48000)."""
    work=outdir/"_work"; work.mkdir(exist_ok=True)
    sr=int(sample_rate or 44100)
    if sr not in (44100,48000,88200,96000):
        sr=44100
    rendered=[]
    items=[(p,c) for p,c in classified.items() if c!="Alignment / Referencia"]
    any_solo=any(settings.get(p,{}).get("solo") for p,_ in items)
    for i,(p,cat) in enumerate(items,1):
        if progress:
            try: progress(i,len(items)+1,f"Procesando {_stem_short_cat(cat)}")
            except Exception: pass
        st=settings.get(p,{})
        dest=work/(p.stem+"_processed.wav")
        src=sources.get(p,p)
        if st.get("mute") or (any_solo and not st.get("solo")):
            run(["ffmpeg","-y","-hide_banner","-loglevel","error","-i",str(src),
                 "-af","volume=0","-ar",str(sr),"-c:a","pcm_f32le",str(dest)])
            rendered.append((dest,cat,p)); continue
        if st.get("tuned_path") and Path(st["tuned_path"]).exists():
            src=Path(st["tuned_path"])
        a=analyze_basic(src)
        fs=stem_recipe(cat,a,st)
        gain=st.get("gain",0)
        if gain:
            fs=list(fs)+[f"volume={10**(gain/20):.8f}"]
        if fs:
            run(["ffmpeg","-y","-hide_banner","-loglevel","error","-i",str(src),"-af",",".join(fs),
                 "-ar",str(sr),"-c:a","pcm_f32le",str(dest)])
        else:
            run(["ffmpeg","-y","-hide_banner","-loglevel","error","-i",str(src),
                 "-ar",str(sr),"-c:a","pcm_f32le",str(dest)])
        rendered.append((dest,cat,p))
    if not rendered: raise RuntimeError("No hay STEMS procesables.")
    if progress:
        try: progress(len(items)+1,len(items)+1,"Mezclando stems…")
        except Exception: pass
    inputs=[]; filters=[]
    for i,(p,cat,orig) in enumerate(rendered):
        filters.append(f"[{i}:a]aresample={sr}[a{i}]")
        inputs += ["-i",str(p)]
    mixins="".join(f"[a{i}]" for i in range(len(rendered)))
    filters.append(mixins+f"amix=inputs={len(rendered)}:duration=longest:normalize=0[m]")
    mix=outdir/(label+"_mix.wav")
    run(["ffmpeg","-y","-hide_banner","-loglevel","error",*inputs,"-filter_complex",";".join(filters),
         "-map","[m]","-ar",str(sr),"-c:a","pcm_f32le",str(mix)])
    return mix,rendered

def _stem_short_cat(cat):
    return {"Beat":"BEAT","Voz principal — Versos":"MAIN VOCAL","Voz principal — Coros":"CHORUS",
            "Backs / Remarques":"BACKS","Adlibs":"ADLIBS","Remarques":"REMARQUES"}.get(cat,cat)

def _probe_duration(path):
    try:
        return float(probe(path).get("format",{}).get("duration") or 0)
    except Exception:
        return 0.0

def verify_audio_tail(path,tail_s=None,burst_db=-18.0,body_ratio_db=6.0):
    """Detecta ráfagas/picos raros en los últimos 3–10 s del archivo.

    Compara el tramo final frente al cuerpo previo. ok=False si hay burst o clip.
    """
    import numpy as np
    path=Path(path)
    try:
        dur=_probe_duration(path)
        if dur < 2.0:
            return {"ok":True,"peak_db":None,"rms_db":None,"reason":"short"}
        # Analizar entre 3 y 10 s de cola según duración.
        take=min(10.0,max(3.0,dur*0.15))
        take=min(take,dur-0.5)
        ss=max(0.0,dur-take)
        sr_an=8000
        r=subprocess.run(
            ["ffmpeg","-v","error","-ss",f"{ss:.4f}","-i",str(path),
             "-t",f"{take:.4f}","-ac","1","-ar",str(sr_an),"-f","f32le","-acodec","pcm_f32le","pipe:1"],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,**_no_window_kwargs())
        if r.returncode:
            return {"ok":True,"peak_db":None,"rms_db":None,"reason":"decode_skip"}
        x=np.frombuffer(r.stdout,dtype="<f4")
        if len(x)<sr_an:
            return {"ok":True,"peak_db":None,"rms_db":None,"reason":"empty"}
        # Últimos 0.4 s vs el resto de la ventana analizada.
        n_tail=max(64,int(sr_an*(tail_s if tail_s is not None else 0.40)))
        body=x[:-n_tail] if len(x)>n_tail*2 else x[:len(x)//2]
        tail=x[-n_tail:]
        def _db(v):
            return 20.0*math.log10(max(float(v),1e-12))
        peak_tail=_db(np.max(np.abs(tail)))
        # Pico máximo en ventanas de 50 ms del tramo analizado (detectar spike aislado)
        win=max(16,int(sr_an*0.05))
        peaks=[]
        for i in range(0,len(x)-win,win):
            peaks.append(_db(np.max(np.abs(x[i:i+win]))))
        if peaks:
            # Spike: un frame mucho más alto que la mediana de la cola
            med=float(np.median(peaks))
            spike=any(p>med+9.0 and p>-6.0 for p in peaks[-max(1,len(peaks)//4):])
        else:
            spike=False
        rms_body=_db(np.sqrt(np.mean(body*body)+1e-20))
        rms_tail=_db(np.sqrt(np.mean(tail*tail)+1e-20))
        burst=(peak_tail>burst_db) and (rms_tail>rms_body+body_ratio_db)
        hard_clip=peak_tail>-1.2
        ok=not (burst or hard_clip or spike)
        return {"ok":ok,"peak_db":peak_tail,"rms_db":rms_tail,"body_rms_db":rms_body,
                "burst":burst,"hard_clip":hard_clip,"spike":spike,"window_s":take}
    except Exception as e:
        return {"ok":True,"peak_db":None,"rms_db":None,"reason":str(e)}

def estimate_linear_ceiling(input_i,input_tp,tp_limit=-1.0):
    """Máximo LUFS aproximado sin aplastar dinámica (ganancia lineal hasta -1 dBTP)."""
    return float(tp_limit)-(float(input_tp)-float(input_i))

def suggest_attainable_target(input_i,input_tp,wanted,tp_limit=-1.0):
    """Propone el preset más cercano alcanzable bajo el techo lineal + margen de limitador ~1.5 LU."""
    ceiling=estimate_linear_ceiling(input_i,input_tp,tp_limit)+1.5
    presets=[-14.0,-12.0,-10.0,-8.0]
    reachable=[p for p in presets if p<=ceiling+0.05]
    if wanted is not None and wanted<=ceiling+0.05:
        return float(wanted),ceiling
    if reachable:
        # Prefer the loudest reachable preset at or below the wanted target.
        below=[p for p in reachable if wanted is None or p<=float(wanted)+0.05]
        return (max(below) if below else max(reachable)),ceiling
    return -14.0,ceiling

def _loudness_filter_chain(gain_db,duration,limit_dbfs=-1.30,heavy=False):
    """Cadena fija: volume + limitador oversampled + fades. Nunca usa loudnorm de render."""
    gain_amp=10.0**(float(gain_db)/20.0)
    limit_amp=10.0**(float(limit_dbfs)/20.0)
    # Fades anti-click / anti-ráfaga al final (más largos si limiting agresivo).
    fade_in=0.003
    fade_out=0.035 if heavy else 0.018
    release=200 if heavy else 140
    parts=[
        f"volume={gain_amp:.10f}",
        "aresample=176400",
        f"alimiter=limit={limit_amp:.10f}:attack=1:release={release}:level=false",
        f"afade=t=in:st=0:d={fade_in:.3f}",
    ]
    if duration and duration>fade_out*3:
        start=max(0.0,float(duration)-fade_out)
        parts.append(f"afade=t=out:st={start:.4f}:d={fade_out:.3f}")
    parts.append("aresample=44100")
    return ",".join(parts)

def apply_loudness(src,target,out):
    """Ganancia fija + limitador oversampled con búsqueda iterativa desde el original.

    - Nunca usa loudnorm dinámico para render (solo medición).
    - Targets comerciales (-14/-12/-10/-8): intenta alcanzarlos aumentando ganancia
      de forma controlada cuando el limitador "come" LUFS; entrega el archivo y avisa
      el sacrificio dinámico.
    - Solo rechaza casos extremos (TP inseguro o error LUFS > ~1.5 tras varios intentos).
    """
    if target is None:
        shutil.copy2(src,out)
        return {"status":"unchanged","target":None}
    out=Path(out); out.parent.mkdir(parents=True,exist_ok=True)
    src=Path(src)
    tolerance_lu=0.5
    soft_tolerance_lu=0.85  # aceptación comercial con aviso
    extreme_lu=1.55
    tp_limit=-1.0
    tp_accept=-0.95
    try: hud().update("Normalizando loudness…",detail=f"Objetivo {float(target):g} LUFS (ganancia fija iterativa)")
    except Exception: pass
    measured=loudnorm(src,target)
    try:
        input_i=float(measured["input_i"])
        input_tp=float(measured["input_tp"])
        input_lra=float(measured.get("input_lra","nan"))
    except (KeyError,TypeError,ValueError):
        raise RuntimeError("No se pudo medir LUFS/true peak de la fuente; se cancela el render.")
    if not math.isfinite(input_i) or not math.isfinite(input_tp):
        raise RuntimeError("Mediciones LUFS/true peak inválidas; se cancela el render.")

    target=float(target)
    requested_gain=target-input_i
    plr=input_tp-input_i
    linear_ceiling=estimate_linear_ceiling(input_i,input_tp,tp_limit)
    estimated_reduction=max(0.0,target-linear_ceiling)
    duration=_probe_duration(src)
    tmp=out.parent/(out.stem+"_fixedgain_work.wav")
    best_path=out.parent/(out.stem+"_fixedgain_best.wav")
    heavy=estimated_reduction>3.0
    limit_dbfs=-1.35 if heavy else -1.30

    # Búsqueda desde el original: cada intento recalcula ganancia; no se apilan renders.
    gain_db=requested_gain
    # Si hace falta limiting fuerte, adelantar un poco la ganancia (el limitador restará LUFS).
    if estimated_reduction>2.0:
        gain_db=requested_gain+min(estimated_reduction*0.55,6.0)

    best=None  # (final_i, final_tp, gain_db, iters, abs_err)
    max_iters=8
    max_gain=requested_gain+18.0
    min_gain=requested_gain-3.0

    for it in range(1,max_iters+1):
        gain_db=max(min_gain,min(max_gain,gain_db))
        try:
            if tmp.exists(): tmp.unlink()
        except OSError: pass
        try: hud().update("Normalizando loudness…",detail=f"Intento {it}/{max_iters} · ganancia {gain_db:+.2f} dB")
        except Exception: pass
        af=_loudness_filter_chain(gain_db,duration,limit_dbfs=limit_dbfs,heavy=heavy or it>2)
        run(["ffmpeg","-y","-hide_banner","-loglevel","error","-i",str(src),
             "-af",af,"-ar","44100","-c:a","pcm_s24le",str(tmp)])
        final=loudnorm(tmp,target)
        try:
            final_i=float(final.get("input_i","nan"))
            final_tp=float(final.get("input_tp","nan"))
        except (TypeError,ValueError):
            final_i=final_tp=float("nan")
        if not (math.isfinite(final_i) and math.isfinite(final_tp)):
            continue
        tp_ok=final_tp<=tp_accept
        err=target-final_i  # >0 → falta loudness (hay que subir ganancia)
        abs_err=abs(err)

        if tp_ok:
            if best is None or abs_err<best[4]:
                shutil.copy2(tmp,best_path)
                best=(final_i,final_tp,gain_db,it,abs_err)
            if abs_err<=tolerance_lu:
                break
            # Ajuste de ganancia: compensar lo que el limitador se comió.
            boost=err*(1.15 if heavy or abs_err>0.4 else 1.05)
            if abs(boost)<0.05:
                break
            gain_db=gain_db+boost
            heavy=True
            limit_dbfs=min(limit_dbfs,-1.32)
            continue

        # TP alto: bajar techo del limitador y no aumentar ganancia.
        limit_dbfs=max(limit_dbfs-0.08,-1.55)
        heavy=True
        if best is not None and best[4]<=soft_tolerance_lu:
            break
        gain_db=gain_db-0.15

    try:
        if tmp.exists(): tmp.unlink()
    except OSError: pass

    if best is None or not best_path.exists():
        raise RuntimeError(
            f"Loudness rechazado: no se pudo obtener una medición válida tras {max_iters} intentos. "
            f"Objetivo={target:g} LUFS."
        )

    final_i,final_tp,gain_db,iters,abs_err=best
    shutil.copy2(best_path,out)
    try: best_path.unlink()
    except OSError: pass

    sacrifice=max(estimated_reduction,max(0.0,gain_db-(tp_limit-input_tp)))
    status="verified"
    if abs_err<=tolerance_lu:
        status="verified"
    elif abs_err<=soft_tolerance_lu:
        status="verified_soft"
    elif abs_err<=extreme_lu and final_tp<=tp_accept:
        # Targets comerciales: entregar aunque el error sea mayor, con aviso fuerte.
        status="delivered_limited"
    else:
        try: out.unlink()
        except OSError: pass
        suggested,_ceil=suggest_attainable_target(input_i,input_tp,target,tp_limit)
        raise RuntimeError(
            f"Loudness rechazado: fuera de rango extremo tras {iters} intentos. "
            f"Objetivo={target:g} LUFS; final={final_i:.2f} LUFS; true peak={final_tp:.2f} dBTP; "
            f"techo lineal≈{linear_ceiling:.1f} LUFS; sugerido≈{suggested:g} LUFS."
        )

    report={"status":status,"target":target,"final_lufs":final_i,
            "final_true_peak_dbtp":final_tp,"fixed_gain_db":gain_db,
            "plr_db":plr,"linear_loudness_ceiling_lufs":linear_ceiling,
            "estimated_dynamic_sacrifice_db":sacrifice,
            "input_lra":input_lra,"lufs_tolerance":tolerance_lu,
            "true_peak_limit_dbtp":tp_limit,"normalization_type":"fixed_gain_limiter",
            "limiter_profile":"iterative_heavy" if heavy else "iterative",
            "limit_dbfs":limit_dbfs,"iterations":iters,"lufs_error":abs_err}
    gui=os.environ.get("MIXFLOW_GUI","").strip() in ("1","true","yes")
    if sacrifice>3.0 or status!="verified":
        msg=(f"ADVERTENCIA: sacrificio dinámico estimado {sacrifice:.1f} dB "
             f"(objetivo {target:g} → {final_i:.2f} LUFS, TP {final_tp:.2f}). "
             "El archivo se entregó; revisa el preview antes de aceptar.")
        if not gui:
            print(msg)
        try: hud().update("Loudness con limiting fuerte",detail=msg)
        except Exception: pass
    if not gui:
        print(f"Loudness OK: {final_i:.2f} LUFS | TP {final_tp:.2f} dBTP | "
              f"ganancia fija {gain_db:+.2f} dB | iters={iters} | {status}")
    # Verificación de cola: detectar ráfagas residuales al final.
    tail=verify_audio_tail(out)
    report["tail_ok"]=bool(tail.get("ok",True))
    report["tail_peak_db"]=tail.get("peak_db")
    report["tail_rms_db"]=tail.get("rms_db")
    if not report["tail_ok"]:
        # Reaplicar fade-out más largo sobre el resultado.
        try:
            repaired=out.parent/(out.stem+"_tailfix.wav")
            dur=_probe_duration(out)
            fade=min(0.08,max(0.04,(dur or 1)*0.02))
            st=max(0.0,(dur or fade)-fade)
            run(["ffmpeg","-y","-hide_banner","-loglevel","error","-i",str(out),
                 "-af",f"afade=t=out:st={st:.4f}:d={fade:.3f}","-ar","44100","-c:a","pcm_s24le",str(repaired)])
            shutil.copy2(repaired,out)
            try: repaired.unlink()
            except OSError: pass
            tail2=verify_audio_tail(out)
            report["tail_ok"]=bool(tail2.get("ok",True))
            report["tail_repaired"]=True
            report["tail_peak_db"]=tail2.get("peak_db")
            report["tail_rms_db"]=tail2.get("rms_db")
        except Exception:
            report["tail_repaired"]=False
    return report

def apply_loudness_with_retry(src,target,out,analysis=None):
    """Solo re-pide nivel en rechazos extremos; targets comerciales suelen entregarse.

    En modo GUI (MIXFLOW_GUI=1) no usa input() de consola: re-lanza el error
    para que la interfaz ofrezca otro nivel.
    """
    while True:
        try:
            apply_loudness(src,target,out)
            return target,Path(out)
        except RuntimeError as exc:
            if not str(exc).startswith("Loudness rechazado:"):
                raise
            if os.environ.get("MIXFLOW_GUI","").strip() in ("1","true","yes"):
                raise
            print("\nNo se pudo resolver este objetivo de forma segura.")
            print(str(exc))
            m=re.search(r"sugerido≈(-?\d+(?:\.\d+)?) LUFS",str(exc))
            if m:
                print(f"Sugerencia: prueba {m.group(1)} LUFS (o un nivel más suave).")
            status,new_target=loudness_choice(analysis)
            if status=="ESC":
                return target,None
            target=new_target

def recommend_loudness(analysis=None):
    if not analysis:
        return "3",-10.0,"Habitual"
    loud=analysis.get("loudness",{})
    try: lufs=float(loud.get("input_i"))
    except (TypeError,ValueError): lufs=-14.0
    try: tp=float(loud.get("input_tp"))
    except (TypeError,ValueError): tp=-1.0
    try: lra=float(loud.get("input_lra"))
    except (TypeError,ValueError): lra=0.0
    crest=float(analysis.get("crest_factor_db",0))
    if tp>-0.3 or lufs>-8.5:
        return "1",-14.0,"Light"
    if lra>12 or crest>16:
        return "2",-12.0,"Básico"
    if lufs<-16:
        return "3",-10.0,"Habitual"
    return "2",-12.0,"Básico"

def loudness_choice(analysis=None):
    rec_key,rec_target,rec_label=recommend_loudness(analysis)
    print("1. Light — Suave (-14 LUFS)\n2. Básico — Normal (-12 LUFS)\n3. Habitual — Comercial (-10 LUFS)\n4. Alto — Muy fuerte (-8 LUFS)\n5. Personalizado\n6. No hacerle nada\nESC → Regresar")
    # Display analysis-derived linear ceiling and estimated dynamic sacrifice beside the choices.
    if analysis and isinstance(analysis,dict):
        loud=analysis.get("loudness",{})
        try:
            inp_i=float(loud["input_i"]); inp_tp=float(loud["input_tp"])
            plr=inp_tp-inp_i; ceiling=-1.0-plr
            print(f"PLR medido: {plr:.1f} dB | límite lineal estimado: {ceiling:.1f} LUFS (techo -1 dBTP)")
            for key,label,target in [("1","Light",-14.0),("2","Básico",-12.0),("3","Habitual",-10.0),("4","Alto",-8.0)]:
                sacrifice=max(0.0,target-ceiling)
                note=" — AVISO: >5 dB; posible aplastamiento" if sacrifice>5.0 else ""
                print(f"  {label}: sacrificio dinámico estimado {sacrifice:.1f} dB{note}")
        except (KeyError,TypeError,ValueError):
            print("PLR/límite lineal no disponible: no se pudo estimar con mediciones válidas.")
    print(f"Sugerencia del análisis: {rec_label} ({rec_target:g} LUFS). Enter = usar esta sugerencia; puedes elegir otro nivel.")
    while True:
        v=input("> ").strip().lower()
        if v=="esc": return "ESC",None
        if not v: return "OK",rec_target
        if v=="6": return "OK",None
        if v in LOUD: return "OK",LOUD[v]
        if v=="5":
            while True:
                raw=input("Objetivo LUFS (-30 a -5, o ESC para volver): ").strip()
                if raw.lower()=="esc": return "ESC",None
                try: custom=float(raw)
                except ValueError:
                    print("Valor no válido. Escribe un número, por ejemplo -11.5.")
                    continue
                if -30.0<=custom<=-5.0: return "OK",custom
                print("Fuera de rango. Usa un objetivo entre -30 y -5 LUFS.")
        print("Opción no válida. Elige 1–6 o ESC.")

def adaptive_mix_filters(analysis):
    """Conservative mix-only EQ/dynamics recipe driven by measured spectrum and dynamics."""
    spectrum=analysis.get("spectrum",{})
    loud=analysis.get("loudness",{})
    filters=["highpass=f=28:p=2"]
    bass=float(spectrum.get("bass_60_150",0))
    lowmid=float(spectrum.get("lowmid_150_350",0))
    presence=float(spectrum.get("presence_2k_5k",0))
    air=float(spectrum.get("air_8k_16k",0))
    if bass>0.30: filters.append("equalizer=f=95:t=q:w=1:g=-0.9")
    elif bass>0.25: filters.append("equalizer=f=95:t=q:w=1:g=-0.45")
    if lowmid>0.28: filters.append("equalizer=f=240:t=q:w=1:g=-0.6")
    elif lowmid>0.24: filters.append("equalizer=f=240:t=q:w=1:g=-0.3")
    if presence<0.16: filters.append("equalizer=f=2800:t=q:w=1:g=0.4")
    elif presence>0.27: filters.append("equalizer=f=3000:t=q:w=1:g=-0.4")
    if air<0.07: filters.append("equalizer=f=10000:t=q:w=0.9:g=0.3")
    elif air>0.18: filters.append("equalizer=f=10000:t=q:w=0.9:g=-0.25")
    try: lra=float(loud.get("input_lra",0))
    except (TypeError,ValueError): lra=0.0
    crest=float(analysis.get("crest_factor_db",0))
    if lra>8 and crest>14:
        filters.append("acompressor=threshold=-18dB:ratio=1.35:attack=20:release=180:makeup=1")
    elif lra>8 and crest>10:
        filters.append("acompressor=threshold=-18dB:ratio=1.2:attack=25:release=220:makeup=1")
    dc=float(analysis.get("dc_offset",0))
    if abs(dc)>0.001:
        filters.append(f"dcshift=shift={max(-0.1,min(0.1,-dc)):.6f}")
    return filters

def normalize_instruction(s):
    s=s.lower().strip()
    replacements={
        "súbele":"subele","súbelo":"subelo","súbanle":"subanle","súbela":"subela",
        "subirle":"subele","subíle":"subele",
        "bájale":"bajale","bájalo":"bajalo","bájenle":"bajenle","bájala":"bajala",
        "más":"mas","está":"esta","están":"estan","aquí":"aqui",
        "escuha":"escucha","escuhan":"escuchan","escuchar":"escuchar","escucha":"escucha","escuchan":"escuchan","se escucha":"se escucha",
        "main vocal":"voz principal","lead vocal":"voz principal",
        "back vocals":"backs","back vocal":"backs","background vocals":"backs",
        "ad libs":"adlibs","ad-libs":"adlibs","remarque":"remarques",
        "terminaciones":"backs / remarques","poquitito":"poquito","un poquitito":"un poquito"
    }
    for a,b in replacements.items():
        s=s.replace(a,b)
    return re.sub(r"\s+"," ",s)

def _mezcla_split_clauses(instruction):
    """Divide frases compuestas sin romper 'un poco' / nombres de banda."""
    parts=re.split(r"\s*(?:\by\b|\bademas\b|\bademás\b|\btambien\b|\btambién\b|,|;|\+)\s*",
                   instruction,flags=re.I)
    return [p.strip() for p in parts if p and p.strip()]

def _mezcla_detect_band(low):
    """Detecta banda espectral aproximada. Orden: específico → genérico."""
    # Defectos tonales / ruido antes que "voz" (p.ej. "la voz se escucha boxed").
    if any(k in low for k in ["boxed","boxy","encajonada","encajonado","caja","cajosa","sonido de caja"]):
        return "boxed"
    if any(k in low for k in ["noise","ruido","ruidos","hiss","siseo","zumbido","hum","fondo ruidoso"]):
        return "noise"
    # Harsh / sibilancia / altos agresivos → presencia (atenuar).
    if any(k in low for k in ["harsh","harshness","agresivo en altos","agresivos en altos",
                              "sibilancia","sibilant","chillona","chillon","estridente","afilado",
                              "en los altos","en los agudos","los altos","los agudos","highs"]):
        if any(k in low for k in ["menos","quita","bajale","reduce","suaviza","atenua","demasiado","muy"]):
            return "presence"
    if any(k in low for k in ["adlibs","adlib","ad libs","ad-libs"]):
        return "adlibs"
    if any(k in low for k in ["backs","back vocal","back vocals","remarques","remarque","remates",
                              "terminaciones","dobles","doblajes","coritos","segunda voz",
                              "segundas voces","voz secundaria","voces secundarias","voz del coro","coros"]):
        return "backs"
    # Voces antes que beat: nunca interpretar "voz/brillo" como beat.
    if any(k in low for k in ["voz principal","main vocal","lead vocal","la voz","las voces",
                              "a la voz","a las voces","de la voz","de las voces","vocal","voz","voces"]):
        if any(k in low for k in ["brillo","brillante","presencia","claridad","aire","opaca","opaco"]):
            return "presence"
        return "vocal"
    if any(k in low for k in ["brillo","brillante","presencia","claridad","aire","opaca","opaco","apagada","apagado"]):
        return "presence"
    # Graves / punch / bajos tonales (no "esta bajo" de nivel).
    level_bajo=any(k in low for k in [
        "muy bajo","muy baja","esta bajo","esta baja","estan bajas","estan muy bajas",
        "estan bajos","se escucha bajo","se oyen bajas","voces bajas","voz baja","volumen bajo"
    ])
    if (not level_bajo) and any(k in low for k in [
            "graves","grave","lows","low end","lowend","punch en","mas punch","más punch",
            "pegada","cuerpo en graves","en los graves","los graves","subgrave","subgraves"]):
        return "body" if any(k in low for k in ["cuerpo","punch","pegada"]) else "beat"
    if (not level_bajo) and any(k in low for k in ["beat","instrumental","pista","base","track",
            "kick","bombo","sub bass","bass","el bajo","al bajo","del bajo"]):
        return "beat"
    if any(k in low for k in ["cuerpo","pecho","peso"]) and "beat" not in low:
        return "body"
    if any(k in low for k in ["pegada","punch","corte","adelante","chillona","nasal"]):
        return "presence"
    return None

def _mezcla_detect_direction(low,band):
    """Dirección up/down; prioriza nivel bajo de voces y atenuaciones explícitas."""
    if band in ("boxed","noise"):
        return "down"
    if any(k in low for k in [
        "voces muy bajas","las voces estan muy bajas","voces estan muy bajas",
        "voz muy baja","las voces estan bajas","voces estan bajas","voz baja","voces bajas",
        "las voces se oyen bajas","las voces suenan bajas","voz enterrada","voces enterradas",
        "voces escondidas","esta enterrada","esta escondida","se escuchan poco","no se escuchan"
    ]):
        return "up"
    down_words=["bajale","bajarlo","bajarle","bajalo","bajenle","bajala","baja ","bajen",
                "quita","quitar","reduce","reducir","disminuye","atenua","atenuar","menos",
                "demasiado fuerte","muy fuerte","muy alto","muy alta","domina","esta encima",
                "retumba","chillona","chillon","nasal","mucho ruido","muy brillante",
                "mas fuerte que","se mete demasiado","demasiado brillante","opaca","opaco","apagada"]
    # "opaca/apagada" implica falta de brillo → up en presence, no down.
    if any(k in low for k in ["opaca","opaco","apagada","apagado","falta brillo","falta presencia",
                              "falta aire","necesita brillo","necesita presencia","le falta brillo",
                              "le falta presencia","mas brillo","mas presencia","mas aire",
                              "dale brillo","dale presencia","brillo a","presencia a"]):
        if not any(k in low for k in ["menos brillo","menos presencia","menos aire","quita brillo",
                                      "demasiado brillante","muy brillante","muy chillona"]):
            return "up"
    if any(k in low for k in down_words):
        return "down"
    up_words=["subele","subelo","subanle","subela","subirle","subir","sube","suban","dale","darle",
              "aumenta","aumentar","realza","realzar","mas volumen","mas fuerte","mas alto","mas alta",
              "muy bajo","muy baja","se escucha poco","no se escucha","esta escondida","esta enterrada",
              "falta","necesita","mas al frente","que corte","poquito","un poco"]
    if any(k in low for k in up_words):
        return "up"
    # "brillo a las voces" sin verbo → realce.
    if band=="presence" and any(k in low for k in ["brillo","presencia","aire"]):
        return "up"
    return None

def _mezcla_strength(band,low):
    """Intensidades: poquito=0.5x, un poco=0.75x, mucho=1.5x."""
    base={"beat":0.20,"adlibs":0.16,"backs":0.16,"vocal":0.12,"presence":0.10,
          "body":0.12,"noise":0.10,"boxed":0.12}.get(band,0.12)
    mult=1.0
    if any(w in low for w in ["poquito","poquitito","apenas","ligeramente","suave"]):
        mult=0.5
    elif any(w in low for w in ["un poco","un poquito"]):
        mult=0.75
    elif any(w in low for w in ["mucho","bastante","demasiado"]):
        mult=1.5
    return min(base*mult,0.32)

def parse_mezcla_feedback(instruction):
    """Traduce lenguaje natural de MEZCLA a filtros FFmpeg / MIXSEL.

    Una sola ruta (sin parser duplicado). Los ajustes son espectrales aproximados
    sobre el estéreo; no separan fuentes. Soporta frases compuestas
    (ej: "más punch en los graves, menos harsh en los altos").
    """
    instruction=normalize_instruction(instruction)
    if not instruction:
        return []
    # Saturación/clipping global → dinámica suave (no EQ).
    if any(k in instruction for k in ["saturad","saturacion","saturación","distorsion","distorsión","clipea","clipping"]):
        return ["acompressor=threshold=-20dB:ratio=1.35:attack=15:release=180:makeup=1"]
    if "compres" in instruction and not _mezcla_split_clauses(instruction)[1:]:
        if any(k in instruction for k in ["menos","bajale","reduce","afloja"]):
            return ["acompressor=threshold=-18dB:ratio=1.15:attack=25:release=220:makeup=1"]
        return ["acompressor=threshold=-18dB:ratio=2.2:attack=20:release=180:makeup=1"]

    actions=[]
    for part in _mezcla_split_clauses(instruction):
        low=normalize_instruction(part)
        if any(k in low for k in ["saturad","saturacion","distorsion","clipea","clipping"]):
            actions.append("acompressor=threshold=-20dB:ratio=1.35:attack=15:release=180:makeup=1")
            continue
        # Atajos semánticos de frases complejas.
        if any(k in low for k in ["punch","pegada"]) and any(k in low for k in ["grave","graves","bass","bajo","lows"]):
            actions.append("MIXSEL:body:up:0.14"); continue
        if any(k in low for k in ["harsh","agresiv","sibil","estridente","afilado"]) and \
           any(k in low for k in ["alto","altos","agudo","agudos","high","menos","quita","suaviza"]):
            actions.append("MIXSEL:presence:down:0.12"); continue
        if any(k in low for k in ["mas cuerpo","más cuerpo","dale cuerpo","cuerpo a"]):
            actions.append("MIXSEL:body:up:0.12"); continue
        if any(k in low for k in ["mas aire","más aire","dale aire","abrir los altos","abre los altos"]):
            actions.append("MIXSEL:presence:up:0.10"); continue
        band=_mezcla_detect_band(low)
        direction=_mezcla_detect_direction(low,band)
        if band is None and any(k in low for k in ["brillo","brillante","opaca","opaco"]):
            band="presence"
            direction=direction or ("down" if any(k in low for k in ["menos","bajale","quita"]) else "up")
        if band is None and any(k in low for k in ["grave","graves","lows","low end"]):
            band="body"
            direction=direction or ("up" if any(k in low for k in ["mas","mas ","punch","pegada","sube","dale"]) else None)
        if band is None:
            continue
        if band=="boxed":
            actions.append("MIXSEL:boxed:down:0.12"); continue
        if band=="noise":
            if any(k in low for k in ["noise","ruido","hiss","siseo"]):
                actions.append("MIXSEL:noise:down:0.10")
            continue
        if direction is None:
            # Default: "en los graves" / "en los altos" con "mas/menos" implícito por contexto.
            if any(k in low for k in ["mas ","más ","dale","sube","aumenta","punch","pegada"]):
                direction="up"
            elif any(k in low for k in ["menos","quita","baja","reduce","suaviza"]):
                direction="down"
            else:
                continue
        # Comparación relativa: "backs mas fuerte que la voz"
        if "mas fuerte que" in low and band in ("backs","adlibs","vocal"):
            if band!="vocal":
                actions.append(f"MIXSEL:{band}:down:{_mezcla_strength(band,low):.2f}")
                actions.append("MIXSEL:vocal:up:0.10")
            else:
                actions.append(f"MIXSEL:vocal:down:{_mezcla_strength(band,low):.2f}")
            continue
        strength=_mezcla_strength(band,low)
        actions.append(f"MIXSEL:{band}:{direction}:{strength:.2f}")

    # Deduplicar conservando orden (última gana por banda+dirección se deja; se apilan distinto).
    seen=set(); out=[]
    for a in actions:
        if a in seen: continue
        seen.add(a); out.append(a)
    return out

def parse_mezcla_feedback_explained(instruction):
    """Igual que parse_mezcla_feedback + resumen humano y flag ambiguous."""
    instruction=normalize_instruction(instruction)
    actions=parse_mezcla_feedback(instruction)
    labels={"beat":"beat","adlibs":"adlibs","backs":"backs","vocal":"voces",
            "presence":"brillo/presencia","body":"cuerpo/graves","noise":"ruido","boxed":"boxed"}
    lines=[]
    for a in actions:
        if a.startswith("MIXSEL:"):
            parts=a.split(":")
            if len(parts)>=4:
                band,dire,st=parts[1],parts[2],parts[3]
                verb="subir" if dire=="up" else "bajar"
                lines.append(f"• {verb} {labels.get(band,band)} (fuerza {st})")
        else:
            lines.append(f"• dinámica: {a[:48]}")
    clauses=_mezcla_split_clauses(instruction)
    ambiguous=False
    if not actions:
        ambiguous=True
    elif len(clauses)>1 and len(actions)<len(clauses):
        ambiguous=True
    # "bajas" sin verbo claro pero con vocales → no debería ser ambiguo si hay acción
    summary="\n".join(lines) if lines else "(sin acciones)"
    return {"actions":actions,"summary":summary,"ambiguous":ambiguous,"clauses":clauses}

def resolve_target(low,classified,last_target=None):
    aliases=[
        ("Voz principal — Coros",[
            "voz principal — coros","voz principal coro","voz principal de coros",
            "principal coro","principal de coros","principal en coros","main vocal coro",
            "main vocal de coros","lead vocal coro","lead en coros"
        ]),
        ("Voz principal — Versos",[
            "voz principal","principal","principal de versos","principal en versos",
            "main vocal","main","lead vocal","lead","voz lead","voz de versos"
        ]),
        ("Segunda voz — Coros",[
            "segunda voz — coros","segunda voz coro","segunda voz de coros",
            "segunda coro","segunda de coros","segunda en coros","second vocal coro"
        ]),
        ("Segunda voz — Versos",[
            "segunda voz — versos","segunda voz de versos","segunda voz",
            "segunda","2da voz","segunda de versos","segunda en versos","second vocal"
        ]),
        ("Remarques",[
            "remarques","remarque","remates","remate","terminaciones","terminacion"
        ]),
        ("Backs / Remarques",[
            "backs / remarques","backs","back",
            "back vocals","back vocal","background vocals"
        ]),
        ("Adlibs",["adlibs","adlib","ad libs","ad-libs","ad libs vocales","adlibs vocales"]),
        ("Beat",["beat","instrumental","pista","base","instrumental beat"]),
        ("Voz principal — Coros",["chorus","coro","coros","main chorus"]),
        ("Voz principal — Versos",["main vocal","lead vocal"])
    ]
    # Prefer exact filename/category mentions first.
    for p,c in classified.items():
        if p.stem.lower() in low or c.lower() in low:
            return p
    # Then semantic aliases.
    for cat,words in aliases:
        if any(w in low for w in words):
            # Coro/verso words disambiguate principal/segunda categories.
            return next((p for p,c in classified.items() if c==cat),None)
    if low.strip() in ("este","esta","eso","esa","ese","el de aqui","la de aqui","el anterior","la anterior"):
        return last_target
    # Generic vocal wording: prefer the most specific already-active target; otherwise main verse.
    if last_target is not None and any(k in low for k in [
        "voz","voces","vocal","opaca","brillo","brillante","cuerpo","delgada",
        "nasal","sibil","aire","compres","enterrada","escondida"
    ]):
        return last_target
    return next((p for p,c in classified.items() if c=="Voz principal — Versos"),None)

def feedback_instruction(low,classified,settings,last_target=None):
    low=normalize_instruction(low)
    target=resolve_target(low,classified,last_target)

    # Comparaciones naturales: "X está más fuerte que Y" means X is too loud;
    # "X está más bajo que Y" means X needs to come up.
    comparison_target=None
    if "mas fuerte que" in low or "mas alta que" in low or "mas alto que" in low:
        left=re.split(r"mas fuerte que|mas alta que|mas alto que",low,1)[0]
        comparison_target=resolve_target(left,classified,last_target)
        if comparison_target is not None: target=comparison_target
        direction="down"
    elif "mas bajo que" in low or "mas baja que" in low:
        left=re.split(r"mas bajo que|mas baja que",low,1)[0]
        comparison_target=resolve_target(left,classified,last_target)
        if comparison_target is not None: target=comparison_target
        direction="up"
    else:
        direction=None

    if target is None: return None
    st=copy.deepcopy(settings.get(target,{}))

    # Level / balance
    loud_down=[
        "bajale","bajalo","bajenle","bajala","muy fuerte","muy alto","muy alta",
        "demasiado fuerte","demasiado alto","demasiado alta","muy encima",
        "se escucha fuerte","se escucha muy fuerte","esta fuerte","esta muy fuerte",
        "esta alto","esta muy alto","esta arriba","se mete demasiado","se mete mucho",
        "se come a","domina","sobresale demasiado","esta demasiado adelante",
        "mas fuerte que"
    ]
    loud_up=[
        "subele","subelo","subanle","subela","muy bajo","muy baja","demasiado bajo",
        "demasiado baja","se escucha bajo","se escucha muy bajo","se escucha poco",
        "esta bajo","esta muy bajo","esta baja","esta muy baja","esta escondida",
        "esta enterrada","esta muy atras","esta atras","no se escucha","casi no se oye",
        "le falta presencia","sale poco","esta tapada"
    ]
    low_level_feedback=any(k in low for k in [
        "voces muy bajas","las voces estan muy bajas","las voces están muy bajas",
        "voces estan muy bajas","voces están muy bajas","voz muy baja","las voces estan bajas",
        "las voces están bajas","voz enterrada","voces enterradas","voces escondidas"
    ])
    if low_level_feedback or direction=="up":
        st["gain"]=st.get("gain",0)+1.5
    elif direction=="down" or any(k in low for k in loud_down):
        st["gain"]=st.get("gain",0)-1.5
    elif any(k in low for k in loud_up):
        st["gain"]=st.get("gain",0)+1.5

    # Stronger explicit amounts.
    if any(k in low for k in ["mucho","bastante","demasiado"]) and any(k in low for k in ["sube","subele","bajo","baja"]):
        st["gain"]=st.get("gain",0)+1.0
    if any(k in low for k in ["mucho","bastante","demasiado"]) and any(k in low for k in ["baja","bajale","fuerte","alto"]):
        st["gain"]=st.get("gain",0)-1.0

    # Compression / dynamics
    if any(k in low for k in ["compres","apretada","apretado","sin dinamica","sin dinámica","demasiado comprimida","demasiado comprimido"]):
        if any(k in low for k in ["menos","baja","bajale","quita","afloja","mas natural","natural"]):
            st["comp_ratio"]=max(1.0,st.get("comp_ratio",2.0)-0.4)
        else:
            st["comp_ratio"]=st.get("comp_ratio",2.0)+0.4

    # Tone
    bright_down=["menos brillo","menos brillante","bajale brillo","demasiado brillante","muy brillante","muy chillona","muy chillón","muy filosa","muy filoso","aguda de mas"]
    bright_up=["mas brillo","mas brillante","subele brillo","falta brillo","falta aire","necesita aire","esta opaca","esta apagada","suena opaca","suena apagada"]
    if any(k in low for k in bright_down): st["bright"]=st.get("bright",0)-0.7
    elif any(k in low for k in bright_up): st["bright"]=st.get("bright",0)+0.7

    body_down=["demasiado cuerpo","muy gruesa","muy grueso","demasiados graves","mucho grave","retumbona","retumbón","bola en graves"]
    body_up=["mas cuerpo","falta cuerpo","esta delgada","esta muy delgada","suena delgada","suena flaca","le falta peso","le falta pecho"]
    if any(k in low for k in body_down): st["body"]=st.get("body",0)-0.7
    elif any(k in low for k in body_up): st["body"]=st.get("body",0)+0.7

    # Other frequent vocal descriptions.
    if any(k in low for k in ["nasal","nasalona","nasalón","suena por la nariz"]):
        st["bright"]=st.get("bright",0)-0.35
        st["body"]=st.get("body",0)+0.2
    if any(k in low for k in ["sibilante","sisea","eses muy fuertes","demasiadas eses"]):
        st["bright"]=st.get("bright",0)-0.5

    # Independent chain request.
    if any(k in low for k in [
        "no uses la misma cadena","otra cadena","otra cadena de voz","usa otra cadena",
        "hazla diferente","hazlo diferente","tratala diferente","trátala diferente",
        "diferente a la principal","diferente de la principal","independiente"
    ]):
        st["unique"]=True

    return target,st

def preview_menu(current,stage,allow_loudness=False,ab_path=None,ab_label="Original"):
    """Menú de preview con reproducción y A/B. Devuelve la opción elegida."""
    current=Path(current)
    while True:
        print("\n"+"-"*72)
        print(f"[ PREVIEW: {stage} ]")
        print(f"Archivo: {current}")
        print("\n  1. ACEPTAR")
        print("  2. AJUSTE (escribe la instrucción después)")
        print("  3. UNDO")
        if allow_loudness:
            print("  4. CAMBIAR LOUDNESS")
        print("  P. Reproducir preview")
        if ab_path:
            print(f"  B. A/B  ({ab_label} ↔ preview)")
        print("  S. Detener reproducción")
        print("  ESC. Regresar")
        print("Elige una opción.")
        try: hud().update(f"Preview listo — {stage}",detail=str(current.name))
        except Exception: pass
        choice=input("> ").strip().lower()
        if choice in ("p","play","reproducir","escuchar"):
            play_audio(current,"preview")
            continue
        if choice in ("s","stop","detener"):
            stop_playback(); print("Reproducción detenida."); continue
        if choice in ("b","ab","a/b","a-b") and ab_path:
            ab_compare(ab_path,current,ab_label,"Preview")
            continue
        if choice in ("b","ab") and not ab_path:
            print("No hay referencia A/B en este paso."); continue
        return choice

def apply_mix_selective(src,out,spec):
    """Ajuste espectral sobre el mix estéreo; no separa fuentes individuales.

    Voz / brillo / adlibs / backs se concentran en ~1.5–5 kHz. Al subirlos se
    atenúan un poco los graves del beat y se compensa el nivel global para que
    la mezcla no suene más “a beat” ni más alta en general.
    """
    # Objetivos no-vocales: un peaking clásico.
    simple_bands={"beat":(110,0.70),"body":(205,0.80),"boxed":(470,0.90),"noise":(10500,0.80)}
    # Objetivos de voz: dos picos en banda vocal + compensación de graves/nivel.
    voice_like={"vocal","presence","adlibs","backs"}
    filters=[]
    for part in spec.split(";"):
        bits=part.strip().split(":")
        if len(bits)<3 or bits[0]!="MIXSEL":
            continue
        target,direction=bits[1],bits[2]
        try:
            strength=float(bits[3]) if len(bits)>3 else 0.15
        except ValueError:
            continue
        gain_db=max(0.4,min(3.0,abs(strength)*10.0))
        if direction!="up":
            gain_db=-gain_db
        if target in voice_like:
            # Dos picos cubren ~1.5–5 kHz sin empujar sub/graves.
            g1=gain_db*0.85
            g2=gain_db*(1.0 if target in ("presence","adlibs") else 0.75)
            # presence/adlibs un poco más arriba; vocal/backs un poco más cuerpo medio.
            f1,f2=(2500,3800) if target in ("presence","adlibs") else (1800,3200)
            filters.append(f"equalizer=f={f1}:t=q:w=1.05:g={g1:.3f}")
            filters.append(f"equalizer=f={f2}:t=q:w=0.95:g={g2:.3f}")
            # Compensación: si sube la voz, baja un poco el beat/graves relativos.
            bass_comp=-abs(gain_db)*0.40 if gain_db>0 else abs(gain_db)*0.25
            filters.append(f"equalizer=f=95:t=q:w=0.85:g={bass_comp:.3f}")
            # Compensación de loudness percibido (evita que todo el mix “suba”).
            level_comp_db=-abs(gain_db)*0.28 if gain_db>0 else abs(gain_db)*0.12
            filters.append(f"volume={10**(level_comp_db/20.0):.8f}")
        elif target in simple_bands:
            freq,q=simple_bands[target]
            filters.append(f"equalizer=f={freq}:t=q:w={q}:g={gain_db:.3f}")
        else:
            continue
    if not filters:
        run(["ffmpeg","-y","-hide_banner","-loglevel","error","-i",str(src),"-c:a","pcm_s24le",str(out)])
        return
    run(["ffmpeg","-y","-hide_banner","-loglevel","error","-i",str(src),"-af",",".join(filters),
         "-ar","44100","-c:a","pcm_s24le",str(out)])

def mezcla_mode():
    total=9
    box("MEZCLA / SELECCIONAR ARCHIVO",1,total)
    src=choose_file("Selecciona la mezcla original WAV")
    if not src: return
    box("ANALIZANDO MEZCLA",2,total,src.name)
    a=analyze_basic(src)
    sp=a.get("spectrum",{})
    dg=a.get("diagnostics",{})
    stereo=dg.get("stereo",{})
    quiet=dg.get("quiet_regions_below_minus55dbfs_min_0_5s",[])
    dyn=dg.get("windowed_rms_dbfs_3s",{})
    analysis_detail=(
        f"Archivo: {src.name}\n"
        f"Duración: {a['duration']:.2f} s | {a['sr']} Hz | {a['channels']} ch\n"
        f"LUFS-I: {a['loudness'].get('input_i')} | LRA: {a['loudness'].get('input_lra')} LU\n"
        f"True Peak: {a['loudness'].get('input_tp')} dBTP\n"
        f"RMS: {a['rms_dbfs']:.2f} dBFS | Peak: {a['peak_dbfs']:.2f} dBFS\n"
        f"Crest: {a.get('crest_factor_db',0):.2f} dB | DC: {a.get('dc_offset',0):.6f}\n"
        f"Espectro: sub={sp.get('sub_20_60',0):.3f}, graves={sp.get('bass_60_150',0):.3f}, "
        f"graves-medios={sp.get('lowmid_150_350',0):.3f}, medios={sp.get('mid_350_2k',0):.3f}, "
        f"presencia={sp.get('presence_2k_5k',0):.3f}, agudos={sp.get('high_5k_8k',0):.3f}, "
        f"aire={sp.get('air_8k_16k',0):.3f}\n"
        f"Muestras cercanas a escala completa (>= 0.999; posible clipping): {dg.get('near_full_scale_sample_count',0)} "
        f"({dg.get('near_full_scale_sample_ratio',0)*100:.5f}%)\n"
        f"Estéreo: correlación L/R={stereo.get('lr_correlation','N/D')} | "
        f"diferencia RMS L-R={stereo.get('left_right_rms_difference_db','N/D')} dB | "
        f"Side/Mid={stereo.get('side_to_mid_db','N/D')} dB\n"
        f"Regiones por debajo de -55 dBFS (>=0.5 s): {len(quiet)} | "
        f"RMS en ventanas de 3 s min/mediana/max={dyn.get('minimum','N/D')}/"
        f"{dyn.get('median','N/D')}/{dyn.get('maximum','N/D')} dBFS | "
        f"cambios bruscos candidatos (>=6 dB/3 s): {len(dyn.get('candidate_energy_transitions',[]))}"
    )
    box("ANÁLISIS COMPLETO",2,total,analysis_detail)
    print("El análisis queda visible antes de continuar.")
    input("Presiona Enter para ver el diagnóstico.")
    box("DIAGNÓSTICO",3,total)
    print("Se aplicarán únicamente correcciones técnicas justificadas por el análisis.")
    box("SELECCIÓN DE LOUDNESS",4,total)
    status,target=loudness_choice(a)
    if status=="ESC": return
    tmp=OUT_ROOT/"Mezcla"/src.stem; tmp.mkdir(parents=True,exist_ok=True)
    base_filters=adaptive_mix_filters(a)
    print("Receta adaptativa propuesta a partir del análisis:")
    for f in base_filters: print(" •",f)
    accepted=list(base_filters)
    history=[[]]
    box("APLICANDO CORRECCIONES",5,total)
    print("Cadena técnica base preparada.")
    def build(filters,tag):
        nonlocal target
        base=tmp/(tag+"_base.wav")
        regular=[f for f in filters if not str(f).startswith("MIXSEL:")]
        selective=[str(f) for f in filters if str(f).startswith("MIXSEL:")]
        try: hud().update("Aplicando EQ / dinámica…",5,total,tag)
        except Exception: pass
        run(["ffmpeg","-y","-hide_banner","-loglevel","error","-i",str(src),"-af",",".join(regular) if regular else "anull",
             "-ar","44100","-c:a","pcm_s24le",str(base)])
        work=base
        for idx,spec in enumerate(selective,1):
            try: hud().update(f"Aplicando ajuste selectivo {idx}/{len(selective)}…",5,total,spec)
            except Exception: pass
            step_out=tmp/(f"{tag}_SELECTIVE_{idx:02d}.wav")
            apply_mix_selective(work,step_out,spec)
            work=step_out
        out=tmp/(tag+"_PREVIEW.wav")
        box("GENERANDO PREVIEW",6,total,f"Procesando desde el WAV original + estado aceptado.")
        try: hud().update("Normalizando loudness…",6,total,"Ganancia fija + limitador (sin loudnorm dinámico)")
        except Exception: pass
        target,rendered=apply_loudness_with_retry(work,target,out,a)
        if rendered is None:
            return None
        out=rendered
        # Tras completar el render, retirar únicamente los intermedios de este tag.
        # El preview final y los estados de undo/aceptación nunca se borran aquí.
        intermediates=[base]+[tmp/(f"{tag}_SELECTIVE_{idx:02d}.wav") for idx in range(1,len(selective)+1)]
        intermediates += list(tmp.glob(tag+"_PREVIEW_loudwork_*.wav"))
        for temp_file in intermediates:
            try:
                if temp_file.exists() and temp_file.resolve()!=out.resolve(): temp_file.unlink()
            except OSError as exc:
                print(f"Aviso: no se pudo eliminar temporal {temp_file.name}: {exc}")
        try: hud().update("Preview listo",6,total,out.name)
        except Exception: pass
        return out
    current=build(accepted,"PREVIEW_01")
    if current is None: return
    while True:
        box("FEEDBACK / AJUSTES",7,total,"El Preview está listo para escuchar.")
        print("Elige: ACEPTAR / AJUSTE / UNDO  |  P = reproducir  |  B = A/B con el original")
        print("En AJUSTE escribe directamente la instrucción natural que quieras.")
        choice=preview_menu(current,"MEZCLA",allow_loudness=True,ab_path=src,ab_label="Original")
        if choice in ("esc","back","regresar"): return
        if choice in ("1","aceptar","ok"): break
        if choice in ("4","loudness","cambiar loudness","cambiar nivel"):
            status,new_target=loudness_choice(a)
            if status=="ESC":
                continue
            old_target=target
            target=new_target
            loudness_labels = {-14.0: "LIGHT", -12.0: "BASICO", -10.0: "HABITUAL", -8.0: "ALTO"}
            if target is None:
                loudness_tag = "SIN_NORMALIZACION"
            elif target in loudness_labels:
                loudness_tag = loudness_labels[target]
            else:
                loudness_tag = f"PERSONALIZADO_{target:g}LUFS"
            new_current=build(base_filters+history[-1],f"LOUDNESS_{loudness_tag}")
            if new_current is None:
                target=old_target
                continue
            current=new_current
            box("PREVIEW CON NUEVO LOUDNESS",7,total,
                f"Nuevo objetivo: {'sin normalización' if target is None else f'{target:g} LUFS'}\nArchivo: {current.name}\nEscucha este preview y elige ACEPTAR, AJUSTE, UNDO o cambia el loudness otra vez.")
            continue
        if choice in ("3","undo"):
            if len(history)>1:
                history.pop(); accepted=base_filters+history[-1]
                restored=build(accepted,f"UNDO_{len(history):02d}")
                if restored is None: return
                current=restored
            else: print("No hay un ajuste aceptado anterior.")
            continue
        if choice in ("2","ajuste"):
            box("AJUSTE / ESPERANDO INSTRUCCIÓN",7,total,"Escribe directamente qué quieres cambiar.")
            instruction=input("Ajuste: ").strip()
            if not instruction:
                continue
            instruction=normalize_instruction(instruction)
            box("INTERPRETANDO AJUSTE",7,total,f'Instrucción recibida: "{instruction}"')
            # MEZCLA: una sola ruta de parser; EQ espectral aproximado (no separa fuentes).
            new_filters=parse_mezcla_feedback(instruction)
            if not new_filters:
                box("AJUSTE NO APLICADO",7,total,f'No pude convertir con seguridad: "{instruction}"')
                print("El estado aceptado no cambió.")
                input("Presiona Enter para volver al Preview.")
                continue
            print("Acciones interpretadas:")
            for f in new_filters: print(" •",f)
            pending=history[-1]+new_filters
            # Título descriptivo corto; si la instrucción es larga, usa fecha y hora.
            slug=re.sub(r"[^A-Za-z0-9]+","_",instruction).strip("_")[:48].strip("_")
            stamp=__import__('datetime').datetime.now().strftime("%H%M%S")
            tag=f"Preview_{slug or 'Ajuste'}" if len(instruction)<=52 else f"Preview_{stamp}"
            pending_current=build(base_filters+pending,tag)
            if pending_current is None:
                continue
            current=pending_current
            verified=analyze_basic(current)
            # pending is not accepted until option 1
            box("PREVIEW NUEVO CREADO",6,total,
                f'Ajuste en PREVIEW: "{instruction}"\n'
                f'Archivo nuevo: {current.name}\n'
                f'LUFS-I: {verified["loudness"].get("input_i")} | '
                f'True Peak: {verified["loudness"].get("input_tp")} dBTP\n'
                f'RMS: {verified["rms_dbfs"]:.2f} dBFS | Peak: {verified["peak_dbfs"]:.2f} dBFS')
            print("Procesamiento realizado y verificado sobre el nuevo Preview.")
            print("El ajuste todavía está PENDIENTE: aún no forma parte del estado aceptado.")
            print("Escucha este nuevo Preview.")
            decision=preview_menu(current,"MEZCLA — AJUSTE PENDIENTE",allow_loudness=True,ab_path=src,ab_label="Original")
            if decision in ("esc","back","regresar"): return
            if decision in ("4","loudness","cambiar loudness","cambiar nivel"):
                status,new_target=loudness_choice(a)
                if status!="ESC":
                    old_target=target
                    target=new_target
                    pending_loud=build(base_filters+pending,f"PENDING_LOUDNESS_{len(history):02d}")
                    if pending_loud is None:
                        target=old_target
                    else:
                        current=pending_loud
                continue
            if decision in ("1","aceptar","ok"):
                history.append([*history[-1],*new_filters]); accepted=base_filters+history[-1]
            elif decision in ("3","undo"):
                restored=build(base_filters+history[-1],f"UNDO_{len(history):02d}")
                if restored is None: return
                current=restored
            else:
                # Rechazar el preview pendiente: volver a renderizar el último estado aceptado.
                restored=build(base_filters+history[-1],f"REJECT_{len(history):02d}")
                if restored is None: return
                current=restored
            continue
    box("MASTER FINAL",8,total)
    final=tmp/(src.stem+"_MASTER_FINAL.wav")
    shutil.copy2(current,final)
    box("ENTREGA WAV FINAL",9,total,str(final))
    print(f"MASTER: {final}")

def stems_mode():
    total=11
    box("STEMS / SELECCIONAR STEMS",1,total)
    files=choose_files("Selecciona todos los STEMS")
    if not files: return
    box("CLASIFICANDO STEMS",2,total)
    classified=ask_classification(files)
    for p,c in classified.items(): print(f"{p.name} → {c}")
    ref=[p for p,c in classified.items() if c=="Alignment / Referencia"]
    if not ref:
        print("\nSelecciona el archivo Alignment / Referencia.")
        for i,p in enumerate(files,1): print(f"{i}. {p.name}")
        x=input("> ").strip()
        if x.isdigit() and 1<=int(x)<=len(files):
            classified[files[int(x)-1]]="Alignment / Referencia"; ref=[files[int(x)-1]]
    tmp=OUT_ROOT/"Stems"/files[0].stem; tmp.mkdir(parents=True,exist_ok=True)
    box("ALIGNMENT / ALINEANDO STEMS",3,total,"Alineación real respecto a Alignment / Referencia; originales intactos.")
    sources=align_stems(classified,ref[0],tmp) if ref else {p:p for p in files}
    box("ANALIZANDO STEMS",4,total)
    for p,c in classified.items():
        if c!="Alignment / Referencia":
            aa=analyze_basic(sources.get(p,p))
            print(f"{c}: {p.name} | RMS {aa['rms_dbfs']:.2f} dBFS | TP {aa['loudness'].get('input_tp')}")
    settings={p:{} for p in classified}
    box("MEZCLA DE STEMS",5,total,"Cadenas independientes por stem vocal. Beat: únicamente volumen/balance.")
    for p,c in classified.items():
        if c!="Alignment / Referencia": print(f"{c}: cadena individual calculada para {p.name}")
    box("SELECCIÓN DE LOUDNESS",6,total)
    status,target=loudness_choice()
    if status=="ESC": return
    box("GENERANDO PREVIEW",7,total)
    preview,_=render_state(sources,classified,settings,tmp,"PREVIEW_01")
    if target is not None:
        loud=tmp/"PREVIEW_01_LOUD.wav"
        target,loud=apply_loudness_with_retry(preview,target,loud)
        if loud is None: return
        preview=loud
    accepted_settings=copy.deepcopy(settings)
    history=[copy.deepcopy(accepted_settings)]
    last_target=None
    while True:
        box("FEEDBACK / AJUSTES",8,total,"PREVIEW listo. No necesitas escribir 'ajustar': selecciona AJUSTE y escribe directamente.")
        # A/B en STEMS: comparar contra el primer preview aceptado de la sesión si existe.
        ab_ref=tmp/"PREVIEW_01_LOUD.wav" if (tmp/"PREVIEW_01_LOUD.wav").exists() else tmp/"PREVIEW_01_mix.wav"
        if not ab_ref.exists(): ab_ref=None
        choice=preview_menu(preview,"STEMS",ab_path=ab_ref,ab_label="Preview base")
        if choice in ("esc","back","regresar"): return
        if choice in ("1","aceptar","ok"): break
        if choice in ("3","undo"):
            if len(history)>1:
                history.pop()
                accepted_settings=copy.deepcopy(history[-1])
                try: hud().update("Restaurando estado (UNDO)…",8,total)
                except Exception: pass
                preview,_=render_state(sources,classified,accepted_settings,tmp,f"UNDO_{len(history):02d}")
                if target is not None:
                    loud=tmp/f"UNDO_{len(history):02d}_LOUD.wav"
                    target,loud=apply_loudness_with_retry(preview,target,loud)
                    if loud is None: return
                    preview=loud
                last_target=None
            else: print("No hay un ajuste aceptado anterior.")
            continue
        if choice in ("2","ajuste"):
            box("AJUSTE / ESPERANDO INSTRUCCIÓN",8,total,"Escribe directamente qué quieres cambiar.")
            instruction=input("Ajuste: ").strip()
            if not instruction:
                continue
            instruction=instruction.lower()
            box("INTERPRETANDO AJUSTE",8,total,f'Instrucción recibida: "{instruction}"')
            result=feedback_instruction(instruction,classified,accepted_settings,last_target)
            if not result:
                box("AJUSTE NO APLICADO",8,total,f'No pude identificar con seguridad qué modificar: "{instruction}"')
                print("El estado aceptado no cambió.")
                input("Presiona Enter para volver al Preview.")
                continue
            target_p,pending_st=result
            pending=copy.deepcopy(accepted_settings); pending[target_p]=pending_st
            try: hud().update("Generando preview de stems…",7,total,classified[target_p])
            except Exception: pass
            preview,_=render_state(sources,classified,pending,tmp,f"PREVIEW_{len(history)+1:02d}")
            if target is not None:
                loud=tmp/f"PREVIEW_{len(history)+1:02d}_LOUD.wav"
                target,loud=apply_loudness_with_retry(preview,target,loud)
                if loud is None: return
                preview=loud
            box("PREVIEW NUEVO CREADO",7,total,f'Corrigiendo: {classified[target_p]} — {target_p.name} | Instrucción: "{instruction}"')
            print("Escucha este nuevo Preview.")
            decision=preview_menu(preview,"STEMS — AJUSTE PENDIENTE",ab_path=ab_ref,ab_label="Preview base")
            if decision in ("esc","back","regresar"): return
            if decision in ("1","aceptar","ok"):
                accepted_settings=pending
                history.append(copy.deepcopy(accepted_settings))
                last_target=target_p
            elif decision in ("3","undo"):
                preview,_=render_state(sources,classified,accepted_settings,tmp,f"UNDO_{len(history):02d}")
                if target is not None:
                    loud=tmp/f"UNDO_{len(history):02d}_LOUD.wav"
                    target,loud=apply_loudness_with_retry(preview,target,loud)
                    if loud is None: return
                    preview=loud
            else:
                # Rechazar el preview pendiente: restaurar únicamente el estado aceptado.
                preview,_=render_state(sources,classified,accepted_settings,tmp,f"REJECT_{len(history):02d}")
                if target is not None:
                    loud=tmp/f"REJECT_{len(history):02d}_LOUD.wav"
                    target,loud=apply_loudness_with_retry(preview,target,loud)
                    if loud is None: return
                    preview=loud
            continue
    box("MASTER FINAL",9,total)
    final=tmp/"STEMS_MASTER_FINAL.wav"; shutil.copy2(preview,final)
    box("EXPORTACIÓN",10,total)
    print("¿Quieres también los stems vocales ya procesados por separado? [S]í / [N]o")
    export=input("> ").strip().lower() in ("s","si","sí","y","yes")
    if export:
        stemout=tmp/"STEMS_VOCALES_PROCESADOS"; stemout.mkdir(exist_ok=True)
        # Re-render accepted state so exports include final accepted gain and processing chain.
        _,rendered=render_state(sources,classified,accepted_settings,tmp,"EXPORT_FINAL")
        for processed,cat,orig in rendered:
            if cat != "Beat" and cat != "Alignment / Referencia":
                shutil.copy2(processed,stemout/(orig.stem+"_PROCESADO.wav"))
        print(f"Stems vocales: {stemout}")
    box("ENTREGA WAV FINAL",11,total)
    print(f"MASTER: {final}")
    if export: print("También se exportaron los stems vocales procesados por separado.")

def snapshot_output_files(root=OUT_ROOT):
    """Snapshot outputs so cleanup never removes files that existed before this run."""
    root=Path(root)
    return {p.resolve() for p in root.rglob("*")} if root.exists() else set()

def cleanup_session_outputs(before, root=OUT_ROOT):
    """Remove only new intermediate files; preserve approved masters and stem exports."""
    root=Path(root)
    if not root.exists(): return []
    removed=[]
    for p in root.rglob("*"):
        if not p.is_file() or p.resolve() in before: continue
        if p.name.endswith("_MASTER_FINAL.wav") or p.name == "STEMS_MASTER_FINAL.wav": continue
        if "STEMS_VOCALES_PROCESADOS" in p.parts and p.name.endswith("_PROCESADO.wav"): continue
        try: p.unlink(); removed.append(str(p))
        except OSError as e: print(f"No se pudo limpiar temporal {p.name}: {e}")
    for p in sorted((x for x in root.rglob("*") if x.is_dir() and x.resolve() not in before),key=lambda x:len(x.parts),reverse=True):
        try: p.rmdir()
        except OSError: pass
    return removed

def main_cli():
    """Modo consola (tests / depuración). La app normal usa la GUI."""
    try: hud().update("Menú principal",detail="Elige MEZCLA o STEMS")
    except Exception: pass
    while True:
        stop_playback()
        print("\n"+"#"*72)
        print("MIXFLOW ASSISTANT — MEZCLA / STEMS")
        print("#"*72)
        print("1. MEZCLA")
        print("2. STEMS")
        print("ESC. Salir")
        try: hud().update("Menú principal",detail="1 = MEZCLA · 2 = STEMS · ESC = salir")
        except Exception: pass
        v=input("> ").strip().lower()
        if v in ("esc","salir","q","quit","exit"):
            stop_playback()
            try: hud().close()
            except Exception: pass
            return 0
        if v in ("1","mezcla"):
            before=snapshot_output_files()
            try: mezcla_mode()
            finally:
                stop_playback()
                cleanup_session_outputs(before)
        elif v in ("2","stems"):
            before=snapshot_output_files()
            try: stems_mode()
            finally:
                stop_playback()
                cleanup_session_outputs(before)
        else: print("Opción no válida.")

def main():
    """Arranque normal: una sola ventana gráfica (MixFlowGUI)."""
    # Permitir consola con: py MixFlowAssistant.py --cli
    if any(a in ("--cli","-c","--console") for a in sys.argv[1:]):
        return main_cli()
    from MixFlowGUI import launch
    launch(hide_console=True)
    return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except KeyboardInterrupt:
        stop_playback()
        try: hud().close()
        except Exception: pass
        print("\nCancelado."); raise SystemExit(0)
    except Exception as e:
        stop_playback()
        # En GUI el error ya se muestra; en CLI pedir Enter.
        if os.environ.get("MIXFLOW_GUI"):
            raise
        print("\nERROR:",e)
        input("Presiona Enter para cerrar...")
        raise
