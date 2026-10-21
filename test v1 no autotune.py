"""V1 no debe aplicar afinación automática oculta.

Sí se permite afinación nota a nota explícita (tune_stem_note_by_note),
disparada por el usuario (AFINAR), sin ganancia automática.
"""
from pathlib import Path
import re
import MixFlowAssistant as m

root=Path(m.__file__).resolve().parent
active_files=[
    root/'MixFlowAssistant.py',
    root/'MixFlow_V2'/'MixFlowAssistant_V2.py',
    root/'MixFlow_V2'/'MixFlowCore.py',
]
for path in active_files:
    if not path.exists():  # MixFlow_V2 is not part of the public repo
        continue
    source=path.read_text(encoding='utf-8')
    for forbidden in (
        # Old automatic / session-wide pitch pipelines (AFINAR nota-a-nota sí permitido)
        r'def\s+(?:detect_pitch|pitch_segments|choose_tune_plan|tuning_preview_loop)\b',
        r'\bautotune\b|\bauto.?tune\b',
        r'segment_targets|tuning_preview_loop|parse_intensity',
    ):
        assert not re.search(forbidden,source,re.I), f'{path.name}: automatic pitch pipeline still present: {forbidden}'
    # rubberband solo dentro de tune_stem_note_by_note (opcional, con formants)
    if path.name=='MixFlowAssistant.py':
        assert 'tune_stem_note_by_note' in source
# API antigua removida; la nueva es explícita y nota a nota.
assert not hasattr(m,'tune_stem') or hasattr(m,'tune_stem_note_by_note')
assert not hasattr(m,'detect_pitch'), 'detect_pitch remains exposed'
assert hasattr(m,'tune_stem_note_by_note'), 'note-by-note tune helper missing'
# stem_recipe no debe inyectar volume automático (solo gain de usuario).
src=(root/'MixFlowAssistant.py').read_text(encoding='utf-8')
# Buscar que stem_recipe no tenga volume= con valores fijos de política
assert 'Sin ganancia automática' in src or 'sin ganancia automática' in src.lower()
print('PASS V1_NO_AUTOMATIC_AUTOTUNE_OPTIONAL_NOTE_TUNE_OK')
