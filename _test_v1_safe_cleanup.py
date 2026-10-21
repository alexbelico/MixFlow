from pathlib import Path
import tempfile
import MixFlowAssistant as m
with tempfile.TemporaryDirectory() as td:
    root=Path(td); old=root/'old_preview.wav'; old.write_bytes(b'old'); olddir=root/'preexisting_empty'; olddir.mkdir()
    before=m.snapshot_output_files(root)
    (root/'new_preview.wav').write_bytes(b'tmp')
    (root/'song_MASTER_FINAL.wav').write_bytes(b'master')
    exp=root/'STEMS_VOCALES_PROCESADOS'; exp.mkdir(); (exp/'lead_PROCESADO.wav').write_bytes(b'vocal')
    (root/'new_subdir').mkdir(); (root/'new_subdir'/'aligned.wav').write_bytes(b'aligned')
    removed=m.cleanup_session_outputs(before,root)
    assert old.read_bytes()==b'old'
    assert olddir.exists() and not any(olddir.iterdir())
    assert not (root/'new_preview.wav').exists()
    assert not (root/'new_subdir'/'aligned.wav').exists()
    assert (root/'song_MASTER_FINAL.wav').read_bytes()==b'master'
    assert (exp/'lead_PROCESADO.wav').read_bytes()==b'vocal'
    print('PASS CLEANUP_PRESERVES_PREEXISTING_MASTER_EXPORTS; removed=',len(removed))
