from pathlib import Path
import sys,builtins,hashlib,json
ROOT=Path(r"C:\Users\andro\OneDrive\Escritorio\Python")
sys.path.insert(0,str(ROOT))
import MixFlowAssistant as m
src=Path(r"C:\Users\andro\Music\blip\Mix puerkjo.wav")
validation_root=Path(r"C:\Users\andro\OneDrive\Escritorio\MixFlow_Output\VALIDACION_AJUSTE_UNDO_REAL_20261009")
m.OUT_ROOT=validation_root
m.choose_file=lambda title: src
answers=iter(["","1","2","súbele a los adlibs","1","3","1"])
old_input=builtins.input
log=[]
def scripted_input(prompt=""):
    try: ans=next(answers)
    except StopIteration: raise RuntimeError("Entrada no prevista: "+prompt)
    log.append({"prompt":prompt,"answer":ans})
    print("SCRIPTED_INPUT",prompt,"=>",repr(ans),flush=True)
    return ans
builtins.input=scripted_input
try:
    print("BEGIN_REAL_ADJUST_UNDO",src,flush=True)
    m.mezcla_mode()
    print("REAL_ADJUST_UNDO_RETURNED",flush=True)
finally:
    builtins.input=old_input
    outdir=validation_root/"Mezcla"/src.stem
    report=[]
    for p in sorted(outdir.glob("*.wav")) if outdir.exists() else []:
        pr=m.probe(p); f=pr["format"]; st=next(s for s in pr["streams"] if s.get("codec_type")=="audio")
        lm=m.loudnorm(p,-14)
        meta={"file":p.name,"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"duration":f.get("duration"),"codec":st.get("codec_name"),"sample_rate":st.get("sample_rate"),"channels":st.get("channels"),"loudness_i":lm.get("input_i"),"true_peak_dbtp":lm.get("input_tp")}
        report.append(meta); print("OUTPUT",json.dumps(meta),flush=True)
    validation_root.mkdir(parents=True,exist_ok=True)
    (validation_root/"REAL_ADJUST_UNDO_REPORT.json").write_text(json.dumps({"source":str(src),"inputs":log,"outputs":report},indent=2,ensure_ascii=False),encoding="utf-8")
    print("REPORT_WRITTEN",validation_root/"REAL_ADJUST_UNDO_REPORT.json",flush=True)
