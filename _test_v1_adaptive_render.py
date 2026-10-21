import tempfile
from pathlib import Path
import numpy as np
import soundfile as sf
import MixFlowAssistant as m

work=Path(tempfile.mkdtemp(prefix='MixFlowV1_adaptive_render_'))
src=work/'source.wav'; out=work/'processed.wav'
sr=44100
t=np.arange(sr*3)/sr
x=(0.1*np.sin(2*np.pi*100*t)+0.05*np.sin(2*np.pi*250*t)+0.001).astype(np.float32)
sf.write(src,x,sr,subtype='PCM_24')
a={'spectrum':{'bass_60_150':0.34,'lowmid_150_350':0.30,'presence_2k_5k':0.12,'air_8k_16k':0.04},'loudness':{'input_lra':'9.5'},'crest_factor_db':15.0,'dc_offset':0.002}
filters=m.adaptive_mix_filters(a)
m.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',str(src),'-af',','.join(filters),'-ar','44100','-c:a','pcm_s24le',str(out)])
assert out.exists() and out.stat().st_size>1000
result=m.analyze_basic(out)
assert result['duration']>2.9 and result['loudness'].get('input_i') is not None
print('PASS ADAPTIVE_FILTER_RENDER',filters)
