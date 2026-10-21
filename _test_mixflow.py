from pathlib import Path
from MixFlowAnalyzer import spectrum
import numpy as np
x=np.sin(2*np.pi*100*np.arange(44100)/44100)
e=spectrum(x,44100)
assert e["bass_60_150"]>0
print("MixFlow spectrum test: OK")
