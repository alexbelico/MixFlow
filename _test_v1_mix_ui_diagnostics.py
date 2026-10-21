import builtins, tempfile, wave
from pathlib import Path
import numpy as np
import MixFlowAssistant as m

sr=44100
t=np.arange(sr*4)/sr
left=0.12*np.sin(2*np.pi*440*t)
right=0.10*np.sin(2*np.pi*440*t)
pcm=np.column_stack([left,right])
pcm=np.clip(pcm*32767,-32768,32767).astype("<i2")
work=Path(tempfile.mkdtemp(prefix="MixFlowV1_ui_diag_"))
src=work/"ui_diag.wav"
with wave.open(str(src),"wb") as wf:
    wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sr); wf.writeframes(pcm.tobytes())

m.choose_file=lambda title:src
captured=[]
m.box=lambda *args,**kwargs:captured.append(args)
m.loudness_choice=lambda *args:("OK",None)
m.preview_menu=lambda *args,**kwargs:"1"
old_input=builtins.input
builtins.input=lambda prompt="":""
try:
    m.mezcla_mode()
finally:
    builtins.input=old_input
analysis=[x for x in captured if x and x[0]=="ANÁLISIS COMPLETO"]
assert analysis, "Analysis panel not emitted"
detail=analysis[0][3]
for key in ["Estéreo:","Regiones por debajo de -55 dBFS","cambios bruscos candidatos","Muestras cercanas a escala completa"]:
    assert key in detail, f"Missing diagnostic in MEZCLA UI: {key}"
print("PASS MIX_MODE_SHOWS_EXTENDED_DIAGNOSTICS")
