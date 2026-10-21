import os, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
TESTS=[
    "_check_final.py",
    "_check_mixflow2.py",
    "_test_mixflow.py",
    "_test_v1_no_autotune.py",
    "_test_v1_alignment.py",
    "_test_v1_adaptive_recipe.py",
    "_test_v1_adaptive_render.py",
    "_test_v1_loudness_recommendation.py",
    "_test_v1_loudness_choice.py",
    "_test_v1_stems_flow.py",
    "_test_v1_feedback_regression.py",
    "_test_v1_parse_mezcla.py",
    "_test_v1_reject_pending_preview.py",
    "_test_v1_stems_reject_pending_preview.py",
    "_test_v1_analyzer_diagnostics.py",
    "_test_v1_mix_ui_diagnostics.py",
    "_test_v1_many_stems_export.py",
    "_test_v1_missing_alignment_reference.py",
    "_test_v1_multi_adjustment_undo.py",
    "_test_v1_stems_multi_adjustment_undo.py",
    "_test_v1_escape_navigation.py",
    "_test_v1_safe_cleanup.py",
]
env=os.environ.copy()
env["PYTHONUTF8"]="1"
results=[]
for name in TESTS:
    p=subprocess.run([sys.executable,str(ROOT/name)],cwd=str(ROOT),env=env,
                     stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                     text=True,encoding="utf-8",errors="replace")
    ok=p.returncode==0
    results.append((name,ok,p.returncode,p.stdout))
    print(("PASS" if ok else "FAIL")+" "+name+" exit="+str(p.returncode),flush=True)
    if not ok:
        print(p.stdout[-5000:],flush=True)
print("\nSUITE_SUMMARY: {}/{} passed".format(sum(x[1] for x in results),len(results)))
if any(not x[1] for x in results):
    sys.exit(1)

