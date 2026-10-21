# MixFlow V1 — Checkpoints de auditoría
Fecha: 2026-10-09
Estado actual: autotune/corrección de pitch retirados del código activo V1 y V2. Alignment se conserva. Suite actual: 21/21 pruebas aprobadas; compilación V1/V2 correcta.

Las notas históricas inferiores que describen afinación corresponden a versiones anteriores al retiro y no describen el código activo actual.

## Verificado
- [x] MEZCLA y STEMS siguen rutas separadas; no hay autotune/corrección de pitch en ninguno de los modos.
- [x] `_test_v1_no_autotune.py` confirma ausencia de funciones y UI de afinación en V1.
- [x] MEZCLA analiza LUFS-I/LRA/true peak, RMS/peak/crest, DC y distribución espectral.
- [x] Panel de MEZCLA muestra correlación L/R, balance RMS L/R, Side/Mid, muestras cercanas a escala completa, regiones de bajo nivel y cambios bruscos candidatos de energía.
- [x] Receta adaptativa conservadora y recomendación de loudness pasan pruebas sintéticas.
- [x] Opción de loudness personalizada, sin cambios, Enter para sugerencia, entradas inválidas y ESC están probados.
- [x] Feedback de MEZCLA para bajar el beat y subir adlibs pasa regresión.
- [x] Rechazar previews pendientes en MEZCLA y STEMS restaura el estado aceptado; los tests comparan SHA-256 del master con el render restaurado.
- [x] UNDO después de dos ajustes aceptados en MEZCLA y STEMS restaura exactamente el estado previo según SHA-256.
- [x] Alineación sintética con offsets de +0.500 s y -0.500 s pasa; envolventes casi constantes no generan offset inventado.
- [x] Si no se reconoce una referencia de alineación, se puede asignar manualmente.
- [x] Clasificación con varios nombres, exportación de seis stems vocales procesados y preservación de originales pasan prueba.
- [x] ESC devuelve al menú desde los modos y sale desde el menú principal.
- [x] Ambos scripts compilan; los tests Unicode se ejecutan con PYTHONUTF8=1.
- [x] Backups checkpoint guardados para MixFlowAssistant.py y MixFlowAnalyzer.py.
- [x] Loudness probado con el WAV original: -14 → -14.00 LUFS / -1.30 dBTP; -12 → -12.02 / -1.11; -10 → -10.36 / -1.11. -8 se rechaza con -9.51 / -1.09 por quedar fuera de la tolerancia. El nivel -10 avisa de sacrificio dinámico estimado de 5.21 dB.

## Limitaciones que siguen abiertas
- [ ] Escuchar y validar calidad con canciones reales: alineación, artefactos, balance vocal/beat y master final.
- [ ] Reproducir el artefacto muy fuerte reportado al final de algunos previews; no se ha confirmado su causa.
- [ ] Detectar estructura musical de forma fiable (verso/coro/puente). El sistema solo marca regiones de bajo nivel y cambios de energía candidatos; no los presenta como secciones musicales.
- [ ] Ampliar matriz de instrucciones naturales de feedback, targets, direcciones y ambigüedades.
- [ ] Probar archivos muy cortos, stems numerosos/extremos, referencia con contenido distinto y cancelación durante procesos largos.
- [ ] Validar la escucha y la exportación de stems procesados de varias categorías.
- [ ] Completar matriz requisito original → función → test → resultado.

## Advertencia funcional importante
En MEZCLA, “subir/bajar beat”, adlibs, backs o voz es un ajuste espectral aproximado del estéreo, no separación real de fuentes. Los elementos que compartan frecuencias también cambiarán.

## Prueba consolidada
La última suite consolidada ejecutó `_run_v1_suite.py`: 21/21 pruebas aprobadas, código de salida 0, duración 87.06 s. Incluye UNDO acumulado de STEMS.


## Checkpoint — interpretación corregida del ZIP (2026-10-09)
- [x] Parámetros por género reclasificados como referencia opcional: el análisis real (LUFS, picos, dinámica, espectro y contexto de la grabación) debe guiar los ajustes adaptativos; no hay receta universal por género.
- [x] Historial persistente entre días rebajado a baja prioridad/no confirmado.
- [x] Inspección de `MixFlowAssistant.py`: los previews y renders intermedios se escriben en carpetas persistentes dentro de `MixFlow_Output`; no se encontró limpieza automática general al terminar.
- [x] Hipótesis a verificar: la referencia a «historial» podría haberse referido a la limpieza automática de previews temporales.
- [ ] Pendiente: revisar salidas normales, ESC/cancelación y tests para definir limpieza segura que conserve máster final y originales. Aún no se modifica código.
- [x] La corrección vocal por segmentos se mantiene como requisito original ya definido; queda por validar si el método actual basado en picos FFT y bloques de 20 s lo satisface.


## Checkpoint — verificación técnica de afinación por segmentos
- [x] `choose_tune_plan()` permite definir nota destino distinta por tramo en un mismo stem.
- [x] `pitch_segments()` divide en bloques fijos de 20 segundos; `tune_stem()` aplica los objetivos por bloque.
- [x] `_test_v1_pitch_segments.py`: PASS.
- [x] `_test_v1_tune_render_segments.py`: PASS; sintetizador 220 Hz → 440 Hz detectado como A3 → A4, duración 40 s conservada.
- [!] Pruebas sintéticas confirman el mecanismo, pero no certifican la precisión con voces reales. FFT de pico predominante puede confundir armónicos; cambios de nota dentro del mismo bloque de 20 s no se segmentan automáticamente.
- [x] Código no modificado durante esta verificación; resultados y limitaciones documentados en el informe de contraste.


## Checkpoint — análisis adaptativo y residuos de previews (2026-10-09)
- [x] Confirmado en el código: el analizador mide LUFS/TP/LRA, RMS/pico/crest, DC, bandas espectrales, diagnósticos estéreo/fase, muestras cercanas a escala completa, silencios y cambios candidatos de energía.
- [x] Confirmado: `adaptive_mix_filters()` usa bandas espectrales, LRA, crest y DC para proponer EQ/compresión/corrección DC; `recommend_loudness()` usa LUFS-I, true peak, LRA y crest. No requiere receta por género.
- [!] Limitación: umbrales fijos sobre proporciones espectrales globales; varios diagnósticos se reportan pero no accionan una corrección automática. Ajustes de beat/adlibs/backs sobre mezcla estéreo son aproximaciones espectrales, no separación de fuentes.
- [x] Inventario real de `MixFlow_Output`: intermedios WAV de preview/base/selective/loudwork y estados undo/reject persisten junto con masters. No se eliminó nada durante la auditoría.
- [ ] Próxima corrección candidata: limpieza segura por sesión solo para temporales generados en esa ejecución; conservar siempre los archivos originales y masters aprobados. Requiere backup y tests de aceptar/cancelar/error antes de editar.
- [x] Se documentó la inspección en `MixFlow_V1_CONTRASTE_REFERENCIA_CLAUDE_20261009.md`, sección 8.3–8.4.


## Checkpoint — cierre de trazabilidad y limpieza segura (2026-10-09)
- [x] Matriz requisito → implementación → prueba creada en `MixFlow_V1_MATRIZ_TRAZABILIDAD_20261009.md`.
- [x] Limpieza de sesión integrada en MEZCLA/STEMS mediante snapshot de archivos antes de ejecutar cada modo y eliminación de archivos nuevos al volver/salir, incluido el caso de excepción.
- [x] Preservación explícita de masters finales, stems vocales procesados exportados y todos los archivos que ya existían antes de la sesión.
- [x] Test aislado `_test_v1_safe_cleanup.py`: PASS.
- [x] `MixFlowAssistant.py` compiló tras el cambio.
- [!] Suite ampliada incluye ahora `_test_v1_safe_cleanup.py`; esperar el resumen de ejecución antes de declarar regresión completa aprobada.
- [!] La prueba audible con voces reales sigue siendo aceptación de calidad de audio; no se confunde con existencia de funciones ni con pruebas sintéticas ya aprobadas.


## Checkpoint final — regresión V1 tras limpieza segura (2026-10-09)
- [x] Compilación: `MixFlowAssistant.py` y `MixFlowAnalyzer.py` sin errores.
- [x] `_test_v1_safe_cleanup.py` pasa, incluyendo preservación de archivo y carpeta vacíos preexistentes, master final, export vocal y borrado de intermedios nuevos.
- [x] Suite consolidada final: **22/22 passed**, exit code 0, runtime 76.66 s.
- [x] Backup previo a limpieza: `MixFlowAssistant.pre_cleanup_20261009_101121.py`.
- [x] Matriz de trazabilidad: `MixFlow_V1_MATRIZ_TRAZABILIDAD_20261009.md`.
- [!] Los intermedios que ya existían antes de una sesión se preservan deliberadamente; no se borraron retrospectivamente para evitar eliminar entregables válidos.
- [!] La escucha con voz real sigue siendo una validación de calidad audible. No invalida las pruebas de existencia/funcionamiento que ya pasaron, pero no debe afirmarse que se certificó el resultado sonoro de una grabación real.
- [x] No se añadieron extras opcionales del ZIP a V1.
