"""Unit tests for MEZCLA natural-language parser (no FFmpeg render required)."""
import MixFlowAssistant as m

def check(instruction, must_contain, must_not=None):
    got=m.parse_mezcla_feedback(instruction)
    text=" | ".join(got)
    for item in must_contain:
        assert any(item in g for g in got), f"{instruction!r} => {got} ; faltaba {item!r}"
    if must_not:
        for item in must_not:
            assert not any(item in g for g in got), f"{instruction!r} => {got} ; no debía tener {item!r}"
    print("PASS", instruction, "=>", got)

check("bájale al beat", ["MIXSEL:beat:down"])
check("súbele el volumen a los adlibs", ["MIXSEL:adlibs:up"])
check("las voces están muy bajas", ["MIXSEL:vocal:up"])
check("brillo a las voces y subirle poquito al beat",
      ["MIXSEL:presence:up", "MIXSEL:beat:up"],
      must_not=["MIXSEL:beat:down"])
# poquito = 0.5x → beat base 0.20 → 0.10
got=m.parse_mezcla_feedback("subirle poquito al beat")
assert got and "0.10" in got[0], got
print("PASS strength poquito", got)
# un poco = 0.75x
got2=m.parse_mezcla_feedback("subirle un poco al beat")
assert got2 and "0.15" in got2[0], got2
print("PASS strength un poco", got2)
# mucho = 1.5x
got3=m.parse_mezcla_feedback("bajale mucho al beat")
assert got3 and "0.30" in got3[0], got3
print("PASS strength mucho", got3)
# compuesto
check("mas punch en los graves, menos harsh en los altos",
      ["MIXSEL:body:up", "MIXSEL:presence:down"])
check("se escucha mucho noise", ["MIXSEL:noise:down"])
check("la voz se escucha boxed", ["MIXSEL:boxed:down"])
print("ALL_PARSE_MEZCLA_TESTS_PASSED")
