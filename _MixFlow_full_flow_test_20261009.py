from pathlib import Path
import sys,builtins,hashlib,json,traceback
ROOT=Path(r"C:\Users\andro\OneDrive\Escritorio\Python")
sys.path.insert(0,str(ROOT))
import MixFlowAssistant as m
src=Path(r"C:\Users\andro\Music\blip\Mix puerkjo.wav")
validation_root=Path(r"C:\Users\andro\OneDrive\Escritorio\MixFlow_Output\VALIDACION_INTEGRAL_REAL_20261009")
m.OUT_ROOT=validation_root
m.choose_file=lambda title: src
answers=iter(["","1","1"])
old_input=builtins.input
log=[]
def scripted_input(prompt=""):
    try:
        ans=next(answers)
    except StopIteration:
        raise RuntimeError("El flujo solicitó una entrada no prevista: "+prompt)
    log.append("INPUT "+prompt+" => "+repr(ans))
    print("SCRIPTED_INPUT",prompt,"=>",repr(ans),flush=True)
    return ans
builtins.input=scripted_input
try:
    print("BEGIN_FULL_MIX_MODE",src,"exists",src.exists(),flush=True)
    m.mezcla_mode()
    print("FULL_MIX_MODE_RETURNED",flush=True)
finally:
    builtins.input=old_input
    outdir=validation_root/"Mezcla"/src.stem
    report=[]
    for p in sorted(outdir.glob("*.wav")) if outdir.exists() else []:
        h=hashlib.sha256(p.read_bytes()).hexdigest()
        try:
            pr=m.probe(p); fmt=pr["format"]; st=next(s for s in pr["streams"] if s.get("codec_type")=="audio")
            meta={"file":p.name,"bytes":p.stat().st_size,"sha256":h,"duration":fmt.get("duration"),"codec":st.get("codec_name"),"sample_rate":st.get("sample_rate"),"channels":st.get("channels")}
        except Exception as e: meta={"file":p.name,"error":str(e)}
        report.append(meta); print("OUTPUT",json.dumps(meta),flush=True)
    (validation_root/"FULL_FLOW_TEST_REPORT.json").write_text(json.dumps({"source":str(src),"source_sha256":hashlib.sha256(src.read_bytes()).hexdigest(),"inputs":log,"outputs":report},indent=2),encoding="utf-8")
    print("REPORT_WRITTEN",validation_root/"FULL_FLOW_TEST_REPORT.json",flush=True)
