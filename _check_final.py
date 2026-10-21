from pathlib import Path
import subprocess,sys
root=Path(__file__).resolve().parent
files=[root/"MixFlowAnalyzer.py",root/"MixFlowAssistant.py",root/"adaptive_master.py"]
for p in files: print(p, "OK" if p.exists() else "MISSING")
for cmd in (["py","--version"],["ffmpeg","-version"],["ffprobe","-version"]):
    p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    print(cmd[0], "OK" if p.returncode==0 else "FAIL")
