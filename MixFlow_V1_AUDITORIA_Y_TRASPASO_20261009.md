# MixFlow V1 — auditoría y continuidad
Fecha: 2026-10-09
Objetivo: terminar **V1** conforme a los requisitos originales. No convertir esta tarea en una ampliación de V2.

## Reglas de trabajo
- No pedir al usuario que vuelva a recopilar capturas o conversaciones ya recuperadas.
- No modificar ni sobrescribir audios originales.
- Antes de editar código, crear copia de seguridad y editar de forma localizada.
- No declarar V1 terminada hasta cerrar la matriz de requisitos y pasar pruebas funcionales.
- Distinguir entre: confirmado, incompleto/defectuoso y no verificado.
- V2 solo se consulta como fuente auxiliar si ayuda a recuperar una especificación; no se debe reemplazar V1 por V2.

## Ubicación del código en el PC
Raíz: `C:\Users\andro\OneDrive\Escritorio\Python\`
- V1 principal: `MixFlowAssistant.py`
- Backup previo existente: `MixFlowAssistant.backup_20261008.py`
- Backup creado antes de esta auditoría: `MixFlowAssistant.pre_V1_audit_20261009.py`
- Analizador auxiliar: `MixFlowAnalyzer.py`
- Launcher: `C:\Users\andro\OneDrive\Escritorio\MixFlow_Assistant.bat`
- Salidas: `C:\Users\andro\OneDrive\Escritorio\MixFlow_Output\`
- V2 (no modificar para esta tarea): `Python\MixFlow_V2\`

## Especificación original que debe preservarse
### Modo MEZCLA
- Selección de una mezcla estéreo, análisis antes de procesar y sin pedir stems/alignment.
- Diagnóstico → propuesta adaptativa → preview → reanálisis/medición → feedback → nuevo preview → aceptar/undo → master WAV.
- El usuario puede describir directamente un ajuste; el estado pendiente no se acepta hasta confirmación.
- Los cambios se reconstruyen desde el original y el estado de ajustes aceptados; no se acumulan renders degradados.
- Los ajustes espectrales sobre estéreo son aproximados y pueden afectar elementos que comparten banda; nunca afirmar que se separaron fuentes.
- Etiquetas de loudness: Light, Básico, Habitual, Alto y Personalizado; análisis previo y posibilidad de no cambiar.
- Original intacto; exports WAV.

### Modo STEMS
- Selección múltiple; clasificación tolerante a nombres variados, con corrección manual cuando haga falta.
- Categorías: voz principal versos/coros, segunda voz versos/coros, adlibs, backs/remarques, beat e alignment/referencia.
- Alignment solo en STEMS.
- Preguntar si se requiere corrección de tono y qué stems vocales; nunca aplicar automáticamente.
- Intensidad Light/Medium/Heavy o 0–100%, con preview, aceptar/ajustar/undo.
- Debe poder usarse una nota objetivo distinta en segmentos diferentes del mismo archivo si la interpretación cambia de nota por secciones.
- Cadenas/ganancia por stem, feedback natural, preview y undo; master WAV y exportación opcional de stems vocales procesados.
- Originales intactos.

## Cambios hechos en esta sesión
1. Se creó `MixFlowAssistant.pre_V1_audit_20261009.py` como backup antes de editar.
2. Se corrigió el parser de feedback de MEZCLA:
   - «bájale al beat» ahora se traduce a `MIXSEL:beat:down:0.2`, no a subida.
   - «súbele el volumen a los adlibs» ahora genera `MIXSEL:adlibs:up:0.16`.
   - Se evita reutilizar la variable `target` del objetivo LUFS, porque eso rompía la normalización al procesar feedback.
3. Pruebas de regresión creadas:
   - `_test_v1_feedback_regression.py`
   - `_test_v1_stems_flow.py`
4. Se ejecutaron correctamente:
   - `py_compile` para los scripts Python del directorio.
   - `_check_final.py` (archivos/dependencias principales disponibles).
   - `_check_mixflow2.py` (NumPy/SciPy disponibles).
   - `_test_mixflow.py` (test de espectro).
   - `_test_v1_feedback_regression.py`: ambos casos pasaron y generaron previews/master.
   - `_test_v1_stems_flow.py`: master de STEMS creado con WAVs sintéticos; se comprobó que los archivos fuente conservaron su tamaño.
5. Los tests sintéticos no equivalen a validación con una mezcla/canción real ni prueban la calidad audible.

## Brechas pendientes — NO declarar V1 terminada
1. **Corrección de tono por segmentos:** ya permite definir y renderizar destinos distintos por tramo de 20 s; las pruebas sintéticas pasan. Falta validar la calidad audible de las transiciones y la precisión del detector con voz real.
2. **Calidad de detección de pitch:** el método usa el pico espectral predominante; puede confundir armónicos con fundamental. No está validado en voz real.
3. **Análisis del modo MEZCLA:** completado parcialmente en esta sesión: incluye espectro por bandas, loudness, crest, DC y receta adaptativa conservadora. La matriz completa debe revisar análisis estéreo/fase, secciones y dinámica más detallada; no afirmar que todos están cubiertos.
4. **Alignment:** ahora usa envolvente RMS a 20 ms y rechaza coincidencias débiles. La prueba controlada confirma corrección de +0.500 s para una fuente adelantada y -0.500 s para una retrasada. Sigue pendiente validar material real y referencias con contenido distinto.
5. **Feedback y targets:** los dos regresiones anteriores están corregidos, pero hay que ampliar la matriz a otros comandos/targets, direcciones, undo y aceptación.
6. **Revisión completa del flujo:** probar cancelación/regreso, loudness personalizado/no-change, varios stems de cada categoría, exportación vocal separada, nombres variados, alignment ausente y archivos cortos.
7. **Matriz de trazabilidad:** cada requisito original debe apuntar a función/línea, prueba y resultado. Los documentos de V2 no sustituyen la especificación original de V1.

## Orden de trabajo recomendado
1. Leer y mapear todas las funciones de V1; crear matriz requisito → implementación → prueba.
2. Alignment se mejoró y se probó sintéticamente; falta validación con material real.
3. La selección de destinos por segmento ya está implementada; validar pitch con voz real y evitar artefactos de transición.
4. Revisar análisis de MEZCLA frente a la especificación original y completar solo las brechas confirmadas.
5. Probar feedback en ambos modos, preview/undo/aceptar, loudness, export y preservación de originales.
6. Ejecutar suite completa, registrar resultados y solo entonces decidir si V1 está lista.

## Estado honesto
La compilación y los tests sintéticos anteriores pasaron; dos fallos de feedback en MEZCLA fueron corregidos. V1 **sigue en auditoría**, no está declarada terminada. No afirmar que se han recuperado todas las horas de trabajo ni que todos los materiales históricos se incorporaron.

## Actualización posterior de esta misma sesión
8. **Alignment actualizado:** ahora compara envolventes RMS de 20 ms, ignora coincidencias débiles y documenta el signo del offset como corrección (positivo retrasa una fuente adelantada; negativo recorta una fuente retrasada). La prueba `_test_v1_alignment.py` pasó en ambos sentidos con offset de ±0.500 s. En señales reales sigue siendo necesario validar confianza y casos donde el contenido de referencia no se parece a la fuente.
9. **Objetivos de afinación por segmentos:** `choose_tune_plan` ahora permite definir una nota destino por cada tramo de 20 s, y `tune_stem` aplica los objetivos por tramo. En la vista previa se muestran los objetivos; el usuario puede cambiar una nota de tramo escribiendo, por ejemplo, `tramo 2 D4`, o cambiar la nota general. Pruebas `_test_v1_pitch_segments.py` y `_test_v1_tune_render_segments.py` pasaron, incluida una señal sintética de 40 s que cambia de A3 a A4.
10. **Suite tras los cambios:** compilación de los scripts y pruebas sintéticas de alignment, feedback y flujo STEMS pasaron. Esto no sustituye la escucha/prueba con material vocal real; el detector actual sigue usando pico espectral predominante, por lo que la precisión de pitch real sigue siendo una brecha por validar.

11. **Análisis y receta adaptativa de MEZCLA:** `analyze_basic` ahora reutiliza `MixFlowAnalyzer.analyze`, incorporando LUFS-I/LRA/true peak, espectro por bandas, crest factor y DC offset. El modo MEZCLA muestra estas métricas antes de procesar y crea una receta conservadora de EQ/dinámica según el espectro medido. Se añadió recomendación inicial de loudness según LUFS/true peak/LRA/crest, con Enter para aceptar la sugerencia o elegir otro nivel. El modo STEMS mantiene la opción de elegir nivel; sin análisis global del master usa sugerencia inicial Habitual.
12. **Pruebas nuevas:** `_test_v1_adaptive_recipe.py`, `_test_v1_adaptive_render.py` y `_test_v1_loudness_recommendation.py`. La primera comprobó receta adaptativa y caso conservador; la segunda ejecutó la cadena completa con FFmpeg (incluyendo compresión y DC shift) y detectó un parámetro de makeup inválido, ya corregido; la tercera pasó los casos de recomendación de loudness.
13. **Suite completa ejecutada tras los cambios de análisis:** compilación Python, dependencias, espectro, receta adaptativa, render adaptativo, recomendación de loudness, alignment, feedback MEZCLA, plan de notas por segmento, render de afinación segmentada y flujo STEMS sintético. Todos los tests de esta suite pasaron después de corregir el parámetro de makeup.


## Checkpoint adicional — 2026-10-09 (revisión de aceptación/rechazo)
14. **Hallazgo reproducible en MEZCLA:** si el usuario generaba un preview de ajuste y en la pantalla de ajuste pendiente elegía una opción distinta de ACEPTAR o UNDO, el flujo podía continuar mostrando ese preview pendiente y copiarlo al master final. Eso contradecía el estado indicado por la interfaz («todavía está PENDIENTE»).
15. **Corrección localizada:** se creó el respaldo `MixFlowAssistant.pre_reject_fix_20261009.py` antes de editar. En `mezcla_mode`, el camino de rechazo ahora vuelve a renderizar `base_filters + history[-1]` con etiqueta `REJECT_...`, es decir, el último estado aceptado.
16. **Prueba específica añadida:** `_test_v1_reject_pending_preview.py` simula un ajuste y su rechazo, verifica que se cree `REJECT_...` y que exista el master final a partir de ese estado. Resultado: `PASS REJECTED_PREVIEW_REVERTS_TO_ACCEPTED_STATE`, salida de proceso 0.
17. **Regresión tras la corrección:** `py -m py_compile MixFlowAssistant.py` completó sin errores; `_test_v1_feedback_regression.py` terminó con `ALL_V1_FEEDBACK_REGRESSION_TESTS_PASSED`; `_test_v1_adaptive_render.py` pasó; `_test_v1_pitch_segments.py` pasó con `PYTHONUTF8=1`; `_test_v1_tune_render_segments.py` pasó; `_test_v1_stems_flow.py` pasó con `PYTHONUTF8=1`; `_test_mixflow.py` y los checks de entorno/dependencias pasaron. Ejecutar los tests que imprimen la flecha Unicode sin UTF-8 puede producir `UnicodeEncodeError` por la consola cp1252 de Windows; al fijar UTF-8, esos tests pasan. No confundir ese problema de consola con un fallo del algoritmo.
18. **Límite de la prueba:** el test de rechazo confirma la ruta de reconstrucción y la presencia del artefacto; todavía falta fortalecer la prueba para comparar contenido de audio/hash o medir que el master sea idéntico al preview aceptado, y probar también rechazo/UNDO después de varios ajustes acumulados.
19. **Estado sigue abierto:** no se han completado las brechas de análisis estéreo/fase, secciones/silencios, validación de afinación con voz real ni la matriz completa de feedback y exportaciones. La corrección de rechazo no significa que V1 esté terminada.

20. **Hallazgo paralelo en STEMS:** la misma clase de defecto existía en la pantalla de ajuste pendiente de STEMS: rechazar el cambio podía dejar el preview pendiente como el que se copiaba al master. Se creó respaldo adicional `MixFlowAssistant.pre_stems_reject_fix_20261009.py` antes de tocar este segundo punto.
21. **Corrección localizada en STEMS:** si el ajuste pendiente no se acepta ni se selecciona UNDO, el flujo ahora vuelve a ejecutar `render_state` con `accepted_tune_plan` y `accepted_settings`, aplicando de nuevo el objetivo de loudness elegido cuando corresponde.
22. **Prueba de rechazo STEMS:** se añadió `_test_v1_stems_reject_pending_preview.py`; simula un ajuste de volumen de voz, lo rechaza y confirma que se genera `REJECT_01_mix.wav` y que el master final se copia desde el estado restaurado. Resultado: `PASS STEMS_REJECTED_PREVIEW_REVERTS_TO_ACCEPTED_STATE`, salida de proceso 0. La compilación de `MixFlowAssistant.py` volvió a pasar.
23. **Checkpoint de seguridad:** las dos rutas (MEZCLA y STEMS) ya tienen restauración explícita tras rechazar un ajuste pendiente y una prueba sintética por separado. Sigue pendiente probar rechazo/UNDO con varios ajustes aceptados acumulados y comparar la señal renderizada, no solo la existencia/tamaño del archivo.

24. **Análisis ampliado:** se añadió a `MixFlowAnalyzer.py` un bloque de diagnósticos calculados por canal: correlación L/R, diferencia de RMS L/R, relación Side/Mid, recuento y proporción de muestras por encima de 0.999, intervalos de bajo nivel inferiores a -55 dBFS de al menos 0.5 s y distribución de RMS por ventanas de 3 s. La interfaz de MEZCLA ahora incluye estos resultados en el panel de análisis.
25. **Prueba sintética del analizador:** `_test_v1_analyzer_diagnostics.py` genera WAV estéreo conocido con un segundo de silencio, canales con polaridad opuesta y diferencia de nivel de aproximadamente 6.02 dB. Resultado: `PASS ANALYZER_STEREO_PHASE_CLIPPING_SILENCE_DYNAMICS`; correlación medida -1.0, diferencia L-R 6.02 dB y silencio detectado entre 0.0 y 1.0 s. `MixFlowAnalyzer.py` y `MixFlowAssistant.py` compilaron sin errores; regresiones de feedback, ambos tests de rechazo, STEMS base, espectro y recomendación de loudness volvieron a pasar.
26. **Limitación explícita:** estos diagnósticos son métricas técnicas, no una detección fiable de verso/coro/puente. Las regiones bajo -55 dBFS se etiquetan como regiones de bajo nivel, no como secciones musicales. La clasificación musical automática por secciones sigue pendiente; también falta escucha de canciones reales para valorar si las métricas ayudan a las decisiones de mezcla.

27. **Precisión de etiquetas:** la métrica basada en muestras >= 0.999 se renombró a `near_full_scale_sample_count/ratio` y la interfaz ahora la describe como muestras cercanas a escala completa que podrían indicar clipping; no se presenta como prueba definitiva de clipping digital.
28. **Verificación reforzada de rechazo:** los tests de rechazo de MEZCLA y STEMS ahora comparan SHA-256 del master final con el WAV `REJECT_...` restaurado, no solo el tamaño. Ambos pasaron después de este cambio; el test del analizador también pasó. Feedback de MEZCLA volvió a pasar tras la actualización de las métricas.

29. **Perfil temporal de energía:** el analizador ahora registra cambios candidatos entre ventanas RMS consecutivas de 3 s cuando la diferencia absoluta es >= 6 dB. La interfaz muestra cuántos candidatos se detectaron. Es un indicador grueso para orientar la revisión; no etiqueta automáticamente verso/coro ni determina por sí solo la estructura musical.
30. **Regresión final de este bloque:** `_test_v1_analyzer_diagnostics.py` incluye ahora un salto de energía controlado y confirmó al menos una transición candidata; el analizador y la interfaz compilaron y el test de feedback volvió a pasar.

31. **Prueba de integración de la interfaz:** `_test_v1_mix_ui_diagnostics.py` ejecutó el modo MEZCLA con un WAV estéreo sintético y verificó que el panel `ANÁLISIS COMPLETO` contiene correlación estéreo, regiones de bajo nivel, candidatos de cambio de energía y muestras cercanas a escala completa. Resultado: `PASS MIX_MODE_SHOWS_EXTENDED_DIAGNOSTICS`.

32. **Alignment: falso positivo detectado y corregido.** La prueba de varios stems con tonos sostenidos mostró que la envolvente RMS casi constante podía generar un offset falso (+0.920 s) aunque los archivos empezaran juntos. Ahora el alineador devuelve 0 s si cualquiera de las envolventes carece de variación suficiente para ofrecer puntos temporales fiables. `_test_v1_alignment.py` pasa los offsets sintéticos de +0.500/-0.500 s y añade `PASS ALIGN_AMBIGUOUS_STEADY_ENVELOPES offset=+0.000s`.
33. **Flujo de varios stems:** `_test_v1_many_stems_export.py` clasificó siete stems de nombres variados y una referencia, completó el master y exportó seis voces procesadas por separado (incluyendo adlibs y backs/remarques). SHA-256 confirmó que los ocho originales quedaron intactos. Resultado: `PASS MULTI_STEM_CLASSIFICATION_EXPORTS_AND_ORIGINAL_PRESERVATION 6`. El falso offset inicial que reveló esta prueba desapareció al repetirla tras la corrección.
34. **Opciones de loudness:** `_test_v1_loudness_choice.py` confirmó el modo sin cambios (`6 → None`), el objetivo personalizado (`5, -11.5 → -11.5`) y aceptar la sugerencia con Enter (`-10 LUFS` en el caso sin análisis).

35. **Referencia de alignment ausente:** `_test_v1_missing_alignment_reference.py` verificó que un archivo no reconocible como referencia puede asignarse manualmente a `Alignment / Referencia`, después el flujo crea el master y mantiene intactos los originales. Resultado: `PASS MANUAL_ALIGNMENT_REFERENCE_SELECTION_AND_ORIGINAL_PRESERVATION`.
36. **UNDO con varios ajustes aceptados:** `_test_v1_multi_adjustment_undo.py` aceptó dos cambios sucesivos, ejecutó UNDO y comparó SHA-256 del master final contra el preview reconstruido `UNDO_02_PREVIEW.wav`. Resultado: `PASS MULTI_ACCEPTED_ADJUSTMENTS_UNDO_RESTORES_PREVIOUS_STATE`.
37. **Backups del checkpoint actual:** se guardaron y verificaron `MixFlowAssistant.checkpoint_20261009_1455.py` (978 líneas) y `MixFlowAnalyzer.checkpoint_20261009_1455.py` (136 líneas) tras los cambios de diagnóstico y alineación.

38. **Navegación ESC:** se actualizó el menú principal para permanecer disponible tras salir de MEZCLA/STEMS; ESC en el menú principal sale, mientras que ESC en los previews de MEZCLA/STEMS devuelve al menú sin finalizar el master. ESC en el preview de afinación cancela el modo STEMS antes de continuar al render.
39. **Selección de loudness validada:** `loudness_choice` ahora vuelve a pedir una opción inválida en vez de elegir silenciosamente el nivel recomendado; el objetivo personalizado valida números y rango de -30 a -5 LUFS. `_test_v1_loudness_choice.py` pasó casos de no-change, custom, Enter, opción inválida y valores personalizados no numéricos/fuera de rango.
40. **Prueba de menú:** `_test_v1_escape_navigation.py` pasó: ejecutó MEZCLA, regresó al menú, ejecutó STEMS y salió por ESC (`PASS ESC_RETURNS_TO_MODE_MENU_AND_EXIT_WORKS`). La compilación de `MixFlowAssistant.py` pasó tras el cambio.

41. ESC dentro de loudness personalizado: escribir ESC en el submenú de objetivo personalizado ahora regresa sin forzar al usuario a introducir un número. _test_v1_loudness_choice.py pasó también el caso ['5','esc'] -> ('ESC', None); compilación y test de navegación ESC volvieron a pasar.

42. Suite de regresión consolidada: se creó _run_v1_suite.py y ejecutó 20 pruebas en secuencia con PYTHONUTF8=1. Resultado final: SUITE_SUMMARY: 20/20 passed; proceso terminó con código 0 en 77.62 s. Incluye entorno, dependencias, espectro, alignment y caso ambiguo, receta/render adaptativo, loudness, afinación por segmentos, flujo STEMS, feedback, rechazo de preview, diagnóstico estéreo/silencio/energía, interfaz de análisis, varios stems/exportación, referencia manual, UNDO acumulado y navegación ESC.
43. Checkpoints verificados tras la suite: MixFlowAssistant.checkpoint_20261009_1510.py y MixFlowAnalyzer.checkpoint_20261009_1510.py. La suite usa señales sintéticas; no certifica la calidad audible de una canción real.

44. Suite actualizada: se añadió _test_v1_stems_multi_adjustment_undo.py al ejecutor y se repitió el conjunto completo. Resultado final: 21/21 passed, exit code 0, runtime 87.80 s. El nuevo test aceptó dos ajustes en STEMS, ejecutó UNDO, comparó SHA-256 del master contra el render restaurado y confirmó preservación de originales.
45. Se actualizó MixFlow_V1_CHECKPOINTS_20261009.md con el resultado 21/21. V1 permanece en auditoría por las limitaciones enumeradas; los resultados sintéticos no certifican calidad audible con canciones reales.

46. Contraste del ZIP pipeline_mastering_spec.zip guardado en MixFlow_V1_CONTRASTE_REFERENCIA_CLAUDE_20261009.md. Se separaron requisitos base, estado observado y mejoras etiquetadas NUEVO/OPCIONAL. No se implementó ninguna sugerencia del ZIP en el código durante este contraste. También se anotaron brechas confirmadas en historial persistente, config por género y detalles del detector/segmentación de afinación.


47. Matriz de trazabilidad V1 creada: `MixFlow_V1_MATRIZ_TRAZABILIDAD_20261009.md`. Mapea requisitos originales a funciones y pruebas concretas; separa implementación verificada, límites técnicos y aceptación audible con audio real. No reabre pruebas ya cerradas ni incorpora extras opcionales del ZIP.
48. Limpieza segura de intermedios añadida al flujo interactivo: antes de cada modo se toma un inventario de archivos existentes y al salir (también ante excepción) se eliminan únicamente archivos nuevos de esa ejecución. Se preservan los archivos preexistentes, los WAV con sufijo `_MASTER_FINAL.wav`, `STEMS_MASTER_FINAL.wav` y los stems vocales exportados `_PROCESADO.wav`. El test aislado verifica que sobreviven un intermedio preexistente, un master aprobado y un stem exportado, mientras se borran preview/alignment nuevos.
49. Backup previo a la limpieza guardado como `MixFlowAssistant.pre_cleanup_20261009_*.py`; el archivo exacto se puede localizar por el timestamp del directorio. Compilación de `MixFlowAssistant.py` pasó tras el cambio. La suite ampliada está en ejecución; no marcarla como aprobada hasta leer el resumen final.


50. Cierre tras el ajuste final de seguridad de carpetas: `MixFlowAssistant.py` y `MixFlowAnalyzer.py` compilan. Se corrigió la limpieza para inventariar también directorios y no intentar borrar directorios vacíos que ya existían antes de la sesión. `_test_v1_safe_cleanup.py` cubre archivo previo, carpeta vacía preexistente, preview nuevo, alignment nuevo, master final y exportación vocal.
51. Regresión final después de esa corrección: `SUITE_SUMMARY: 22/22 passed`, código de salida 0, runtime 76.66 s. Incluye `_test_v1_safe_cleanup.py` más las 21 pruebas previas. Este es el resultado final vigente.
52. Backup de código previo a la limpieza: `MixFlowAssistant.pre_cleanup_20261009_101121.py`. Los intermedios antiguos que ya existían antes de cada ejecución se conservan intencionalmente por seguridad; la limpieza nueva elimina los intermedios creados en esa sesión, no hace borrado retroactivo masivo.
53. Estado de cierre: implementación y regresión automatizada de V1 completadas en el alcance documentado. La matriz explicita dos límites de comportamiento ya conocidos (ajustes espectrales aproximados en estéreo y afinación por bloques fijos de 20 s) y que la escucha con una voz real es validación de calidad audible, no una prueba de existencia de la función. No se certifica calidad sonora universal sin esa aceptación real.


## Actualización de cierre técnico — 2026-10-09

- **Autotune/corrección de pitch retirados del código activo V1 y V2.** Se eliminaron las funciones de detección/segmentación/afinación, la UI y los parámetros de intensidad; `_test_v1_no_autotune.py` verifica ambos árboles activos. Alignment/Referencia se conserva y no se considera afinación.
- Las copias de código históricas previas al retiro se movieron, sin borrarlas, a `C:\Users\andro\OneDrive\Escritorio\MixFlow_Legacy_Backups_Pre_Autotune_Removal_20261009`. El backup activo de seguridad coincide por SHA-256 con el código V1 final.
- Se ajustó el techo del limitador de -1.05 a -1.25 dBFS para dejar margen a los overs entre muestras. Prueba sobre el preview real de 153.83 s: objetivo -14 → -14.00 LUFS / -1.19 dBTP; -12 → -12.08 / -1.11; -10 → -10.45 / -1.11. El objetivo -8 se rechazó porque produjo -9.49 LUFS, fuera de la tolerancia de ±0.5 LU. Prueba directa sobre el WAV original `C:\\Users\\andro\\Music\\blip\\Mix puerkjo.wav`: -14 → -14.00 LUFS / -1.30 dBTP; -12 → -12.02 / -1.11; -10 → -10.36 / -1.11. El objetivo -8 se rechazó porque produjo -9.51 LUFS / -1.09 dBTP, fuera de tolerancia. El objetivo -10 cumple la tolerancia, pero el análisis advierte un sacrificio dinámico estimado de 5.21 dB; se deja al usuario escuchar el preview antes de aceptarlo. El flujo vuelve a pedir otro nivel en vez de cerrar la sesión por un rechazo de loudness.
- Compilación Python de V1, analizador y V2 correcta. Suite final `_run_v1_suite.py`: **21/21 pruebas aprobadas**, incluida la prueba de ausencia de autotune y el reintento de loudness rechazado.
- Los tres previews existentes se conservaron intactos. Se localizó el original en `C:\\Users\\andro\\Music\\blip\\Mix puerkjo.wav`. El último segundo de los previews no contiene un pico alto (máximo medido aproximadamente -65.2 dBFS); hay transitorios entre 134–146 s tanto en el original como en los previews. Los picos de los previews son menores que los del original en esas ventanas, por lo que el análisis numérico no confirma un pico nuevo generado al final. La percepción del sonido tipo disparo requiere escucha A/B; no se marca como solucionada sin esa verificación audible.
