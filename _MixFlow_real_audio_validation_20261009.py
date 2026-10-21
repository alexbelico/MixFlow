from pathlib import Path
import sys, json, hashlib, re, traceback
ROOT=Path(r"C:\Users\andro\OneDrive\Escritorio\Python")
sys.path.insert(0,str(ROOT))
import MixFlowAssistant as m
src=Path(r"C:\Users\andro\Music\blip\Mix puerkjo.wav")
outdir=Path(r"C:\Users\andro\OneDrive\Escritorio\MixFlow_Output\Mezcla\Mix puerkjo\VALIDACION_REAL_20261009")
outdir.mkdir(parents=True,exist_ok=True)
log=[]
def say(*a):
    s=" ".join(str(x) for x in a); print(s,flush=True); log.append(s)
try:
    if not src.exists(): raise FileNotFoundError(src)
    say("SOURCE",src,"bytes",src.stat().st_size)
    a=m.analyze_basic(src)
    say("ANALYSIS",json.dumps({k:a.get(k) for k in ("duration","sr","channels","codec","peak_dbfs","rms_dbfs","crest_factor_db","dc_offset")},ensure_ascii=False))
    say("LOUDNESS_INPUT",json.dumps(a.get("loudness",{}),ensure_ascii=False))
    say("SPECTRUM",json.dumps(a.get("spectrum",{}),ensure_ascii=False))
    filters=m.adaptive_mix_filters(a)
    say("ADAPTIVE_FILTERS",json.dumps(filters,ensure_ascii=False))
    base=outdir/"00_PREVIEW_PROCESSED_BEFORE_LOUDNESS.wav"
    m.run(["ffmpeg","-y","-hide_banner","-loglevel","error","-i",str(src),"-af",",".join(filters),"-ar","44100","-c:a","pcm_s24le",str(base)])
    say("BASE_RENDER_OK",base.exists(),base.stat().st_size if base.exists() else 0)
    report=m.apply_loudness(base,-14.0,outdir/"01_PREVIEW_REAL_LIGHT_-14LUFS.wav")
    say("LIGHT_REPORT",json.dumps(report,ensure_ascii=False))
    selective=outdir/"02_PREVIEW_REAL_SELECTIVE_ADLIBS_EQ.wav"
    m.apply_mix_selective(base,selective,"MIXSEL:adlibs:up:0.16")
    say("SELECTIVE_RENDER_OK",selective.exists(),selective.stat().st_size if selective.exists() else 0)
    report2=m.apply_loudness(selective,-14.0,outdir/"03_PREVIEW_REAL_SELECTIVE_ADLIBS_EQ_LIGHT_-14LUFS.wav")
    say("SELECTIVE_LIGHT_REPORT",json.dumps(report2,ensure_ascii=False))
    # verify each output can be probed and has matching duration/channels/sample rate
    for p in [base,outdir/"01_PREVIEW_REAL_LIGHT_-14LUFS.wav",selective,outdir/"03_PREVIEW_REAL_SELECTIVE_ADLIBS_EQ_LIGHT_-14LUFS.wav"]:
        pr=m.probe(p); f=pr["format"]; st=next(s for s in pr["streams"] if s.get("codec_type")=="audio")
        say("OUTPUT_PROBE",p.name,"duration",f.get("duration"),"codec",st.get("codec_name"),"sr",st.get("sample_rate"),"channels",st.get("channels"),"bytes",p.stat().st_size)
    # scan only active V1/V2 Python sources for pitch-correction implementation
    active=[ROOT/"MixFlowAssistant.py",ROOT/"MixFlowAnalyzer.py",ROOT/"MixFlow_V2"/"MixFlowAssistant_V2.py",ROOT/"MixFlow_V2"/"MixFlowCore.py"]
    pat=re.compile(r"autotune|auto.?tune|pitch.?correction|pitch_correct|detect_pitch|rubberband|pyin|crepe|afinaci[oó]n vocal|tuning_preview|target_midi|pitch_segments|tune_stem",re.I)
    hits=[]
    for p in active:
        for i,line in enumerate(p.read_text(encoding="utf-8",errors="replace").splitlines(),1):
            if pat.search(line): hits.append(f"{p.name}:{i}:{line.strip()}")
    say("NO_AUTOTUNE_SCAN", "PASS" if not hits else "FAIL",json.dumps(hits[:20],ensure_ascii=False))
    say("VALIDATION_DONE")
except Exception as e:
    say("VALIDATION_FAIL",type(e).__name__,str(e))
    traceback.print_exc()
finally:
    (outdir/"VALIDACION_REAL_LOG.txt").write_text("\n".join(log)+"\n",encoding="utf-8")
