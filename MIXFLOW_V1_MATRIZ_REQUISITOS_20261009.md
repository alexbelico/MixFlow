# MixFlow V1 — matriz de trazabilidad
Actualización: 2026-10-09
Estados: **Implementado y probado sintéticamente**, **Implementado; prueba parcial**, **Pendiente / no verificado**.

| Área | Requisito | Implementación actual | Evidencia/prueba | Estado |
|---|---|---|---|---|
| Flujo general | Elegir MEZCLA o STEMS | `main()` | Compilación y flujos sintéticos | Implementado; prueba parcial |
| MEZCLA | Analizar antes de proponer procesamiento | `analyze_basic()`, `MixFlowAnalyzer.analyze()` | Análisis incluye LUFS/LRA/TP, RMS/peak, espectro, crest y DC | Implementado; prueba parcial |
| MEZCLA | Receta conservadora según mediciones | `adaptive_mix_filters()` | `_test_v1_adaptive_recipe.py`, `_test_v1_adaptive_render.py` | Implementado y probado sintéticamente |
| MEZCLA | Mostrar diagnóstico antes de procesar | `mezcla_mode()` | Mensaje de análisis/receta en consola | Implementado; prueba parcial |
| MEZCLA | Niveles Light/Básico/Habitual/Alto/Personalizado y no cambiar | `loudness_choice()` | `_test_v1_loudness_recommendation.py`; opción no-change usa copia | Implementado; prueba parcial |
| MEZCLA | Recomendar loudness con base en el análisis, permitir elección manual | `recommend_loudness()`, `loudness_choice(a)` | Casos de LUFS/TP/LRA/crest en test | Implementado y probado sintéticamente |
| MEZCLA | Feedback natural para ajustar beat, voz, adlibs y otras bandas | Parser en `mezcla_mode()`, `apply_mix_selective()` | `_test_v1_feedback_regression.py` cubre beat down y adlibs up | Implementado; matriz de lenguaje incompleta |
| MEZCLA | Previsualizar ajuste pendiente y aceptarlo o descartarlo | Bucle de preview y `preview_menu()` | Regresión acepta ajuste pendiente; undo no cubierto exhaustivamente | Implementado; prueba parcial |
| MEZCLA | Undo de ajuste aceptado | Historial `history` en `mezcla_mode()` | Sin prueba exhaustiva de secuencias de múltiples cambios | Pendiente de verificación |
| MEZCLA | Ajuste espectral no debe fingir separación de fuentes | Filtros por banda en el mix estéreo | Comentario y bandas de `apply_mix_selective()` | Implementado como aproximación; comprobar percepción audible |
| MEZCLA | Análisis estéreo/fase, secciones temporales y calidad gate | No cubierto de forma integral en V1 | No hay test completo que lo demuestre | Pendiente / no verificado |
| STEMS | Selección múltiple y clasificación tolerante de nombres | `choose_files()`, `classify()`, `ask_classification()` | Flujo sintético con voz, beat y reference | Implementado; probar más variantes |
| STEMS | Alignment solo en STEMS | `align_stems()` llamado por `stems_mode()` | `_test_v1_alignment.py` | Implementado y probado sintéticamente |
| STEMS | Alineación con reference sin falsos desplazamientos evidentes | Envolvente RMS a 20 ms, threshold de correlación | Desplazamientos sintéticos ±0.5 s correctos | Implementado; falta validación con fuentes musicales distintas |
| STEMS | Sin autotune ni corrección de pitch en V1 | No hay interfaz ni funciones de afinación en `MixFlowAssistant.py` | `_test_v1_no_autotune.py` + suite V1 | Eliminado del alcance de V1 |
| STEMS | Procesamiento/ganancia por stem y feedback | `stem_recipe()`, `feedback_instruction()`, `render_state()` | Flujo STEMS sintético básico | Implementado; matriz de feedback pendiente |
| STEMS | Exportar master WAV y stems vocales procesados opcionales | `STEMS_MASTER_FINAL.wav`, `STEMS_VOCALES_PROCESADOS` | Master probado; export separado no cubierto en la última suite | Implementado; export pendiente de prueba |
| General | Originales de audio intactos | Renders en `MixFlow_Output` | `_test_v1_stems_flow.py` compara tamaños de originales | Probado sintéticamente |
| General | No sobrescribir salida anterior inadvertidamente | Carpetas por nombre de sesión; nombres de preview fijos | Puede reusar carpeta si se repite el mismo nombre | Pendiente de decisión/validación |
| General | Exportar WAV y verificar loudness final/true peak | `apply_loudness()`, archivos WAV | Previews se miden; falta quality gate final completo | Implementado parcialmente |
| General | Matriz completa basada en todos los requisitos originales recuperados | Este archivo es una primera matriz basada en evidencia disponible | No se pudo recuperar aquí el texto íntegro de todos los ZIP históricos | Pendiente; no pedir al usuario que recopile de nuevo |

## Resultado provisional
Hay progreso funcional verificable, pero esta matriz **no autoriza declarar V1 terminada**. Lo más importante pendiente es completar las pruebas de undo/export/feedback y cotejar cualquier requisito original que aún no tenga evidencia directa. La afinación vocal fue retirada de V1; no forma parte del flujo activo.
