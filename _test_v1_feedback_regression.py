import builtins, subprocess, tempfile
from pathlib import Path
import MixFlowAssistant as m

work = Path(tempfile.mkdtemp(prefix='MixFlowV1_regression_'))
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

def run_case(instruction, expected):
    global seen
    seen=[]
    answers=iter(['', '2', instruction, '1', '1'])
    original_input=builtins.input
    builtins.input=lambda prompt='': next(answers)
    try:
        m.mezcla_mode()
    finally:
        builtins.input=original_input
    assert seen, f'No se aplicó ajuste para: {instruction}'
    assert expected in seen[0], f'{instruction}: esperado {expected}, recibido {seen[0]}'
    print('PASS', instruction, '=>', seen[0])

run_case('bájale al beat', 'MIXSEL:beat:down:0.2')
run_case('súbele el volumen a los adlibs', 'MIXSEL:adlibs:up:0.16')
print('ALL_V1_FEEDBACK_REGRESSION_TESTS_PASSED')
