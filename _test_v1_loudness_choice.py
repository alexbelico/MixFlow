import builtins
import MixFlowAssistant as m

def run_case(values,expected):
    seq=iter(values)
    old=builtins.input
    builtins.input=lambda prompt="":next(seq)
    try: got=m.loudness_choice()
    finally: builtins.input=old
    assert got==expected,(values,got,expected)
    print("PASS LOUDNESS_CHOICE",values,"=>",got)
run_case(["6"],("OK",None))
run_case(["5","-11.5"],("OK",-11.5))
run_case([""],("OK",-10.0))
run_case(["9","6"],("OK",None))
run_case(["5","abc","-31","-11.5"],("OK",-11.5))
run_case(["5","esc"],("ESC",None))

# A rejected high target must return to level selection rather than crash the workflow.
from pathlib import Path
original_apply=m.apply_loudness
original_choice=m.loudness_choice
attempts=[]
def fake_apply(src,target,out):
    attempts.append(target)
    if target==-8.0:
        raise RuntimeError('Loudness rechazado: test de recuperación')
def fake_choice(analysis=None):
    return ('OK',-10.0)
m.apply_loudness=fake_apply
m.loudness_choice=fake_choice
try:
    chosen,out=m.apply_loudness_with_retry(Path('source.wav'),-8.0,Path('preview.wav'))
finally:
    m.apply_loudness=original_apply
    m.loudness_choice=original_choice
assert chosen==-10.0 and attempts==[-8.0,-10.0],(chosen,attempts)
print('PASS LOUDNESS_REJECT_REPROMPTS_WITHOUT_CRASH')
