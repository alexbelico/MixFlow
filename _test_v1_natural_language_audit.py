import builtins, subprocess, tempfile
from pathlib import Path
import MixFlowAssistant as m

work = Path(tempfile.mkdtemp(prefix='MixFlowV1_nlcheck_'))
src = work / 'testmix.wav'
subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','lavfi','-i','aevalsrc=0.1*sin(2*PI*100*t)+0.1*sin(2*PI*1000*t):s=44100:d=3','-c:a','pcm_s24le',str(src)],check=True)
m.choose_file = lambda title: src
m.box = lambda *args, **kwargs: None
m.loudness_choice = lambda *args: ('OK', None)
seen=[]
original_apply=m.apply_mix_selective
def capture(src_path,out_path,spec):
    seen.append(spec)
    return original_apply(src_path,out_path,spec)
m.apply_mix_selective=capture

cases = [
 'bájale al beat',
 'bájale volumen al beat un poquito',
 'bájale el bass al beat',
 'le falta brillo a la voz principal',
 'la voz se escucha boxed',
 'todo el tema en general se escucha saturado',
 'la voz principal se escucha saturada',
 'súbele a los adlibs',
 'súbele a los remarques',
 'súbele a la main vocal',
 'súbele un poquitito a la voz principal',
 'se escucha mucho noise',
 'dale más presencia a los adlibs',
 'dale más presencia a las segundas voces',
 'brillo a las voces y subirle poquito al beat',
 'las voces están muy bajas',
]
for instruction in cases:
    seen.clear()
    answers=iter(['', '2', instruction, '1', '1'])
    original_input=builtins.input
    builtins.input=lambda prompt='': next(answers)
    error=None
    try:
        m.mezcla_mode()
    except Exception as e:
        error=f'{type(e).__name__}: {e}'
    finally:
        builtins.input=original_input
    print(('ERROR' if error else 'RESULT'), repr(instruction), '=>', seen[:4], error or '')
