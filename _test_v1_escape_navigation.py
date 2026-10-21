import builtins
import MixFlowAssistant as m

calls=[]
m.mezcla_mode=lambda:calls.append("mezcla")
m.stems_mode=lambda:calls.append("stems")
answers=iter(["1","2","esc"])
old=builtins.input
builtins.input=lambda prompt="":next(answers)
try:
    code=m.main_cli()  # consola; main() abre la GUI
finally:
    builtins.input=old
assert code==0
assert calls==["mezcla","stems"],calls
print("PASS ESC_RETURNS_TO_MODE_MENU_AND_EXIT_WORKS")
