# MixFlow V1 — matriz de trazabilidad de cierre
Fecha: 2026-10-09
Código evaluado: MixFlowAssistant.py + MixFlowAnalyzer.py
Alcance: requisitos V1 documentados en la auditoría y contraste de referencia. No incluye extras opcionales del ZIP.

| Requisito V1 | Implementación observada | Evidencia automatizada | Estado |
|---|---|---|---|
| Separar modos MEZCLA y STEMS | Menú con ambos flujos; alignment solo en STEMS | _test_v1_stems_flow.py; _test_v1_escape_navigation.py | Implementado y probado |
| Analizar mezcla antes de procesar | LUFS-I, TP, LRA, RMS, pico, crest, DC, espectro y diagnósticos estéreo/energía | _test_v1_analyzer_diagnostics.py; _test_v1_mix_ui_diagnostics.py | Implementado y probado con señales sintéticas |
| Receta adaptativa basada en análisis, no género | EQ condicional según bandas, compresión según LRA/crest, corrección DC | _test_v1_adaptive_recipe.py; _test_v1_adaptive_render.py; _test_v1_loudness_recommendation.py | Implementado y probado con señales sintéticas |
| Preview, feedback, aceptar/rechazar/UNDO en MEZCLA | Render desde original + estado aceptado; rechazo reconstruye estado aceptado | _test_v1_feedback_regression.py; _test_v1_reject_pending_preview.py; _test_v1_multi_adjustment_undo.py | Implementado y probado |
| Ajustes de beat/adlibs/backs sobre estéreo | Filtros espectrales aproximados; no separación de fuentes | _test_v1_feedback_regression.py | Implementado; limitación documentada |
| Etiquetas de loudness, personalizado y no cambiar | Light/Básico/Habitual/Alto/Personalizado; validación de rango y entradas | _test_v1_loudness_choice.py; _test_v1_loudness_recommendation.py | Implementado y probado |
| Clasificar stems con nombres variables y referencia manual | Clasificación por nombre + elección manual; referencia Alignment | _test_v1_many_stems_export.py; _test_v1_missing_alignment_reference.py | Implementado y probado |
| Alineación respecto a referencia sin tocar originales | Estimación de envolvente; casos ambiguos dejan offset en cero | _test_v1_alignment.py; _test_v1_many_stems_export.py | Implementado y probado con señales sintéticas |
| Sin autotune ni corrección de pitch | No existen funciones ni interfaz de afinación en el código activo | _test_v1_no_autotune.py + suite V1 | Eliminado y verificado |
| Procesamiento individual y master de stems; exportación vocal opcional | Cadenas por stem, master final y exportación opcional de stems procesados | _test_v1_many_stems_export.py; _test_v1_stems_flow.py | Implementado y probado |
| Preservar originales y flujo de cancelación/UNDO | Tests verifican hashes, rechazo y UNDO; navegación ESC regresa/sale según menú | _test_v1_reject_pending_preview.py; _test_v1_stems_reject_pending_preview.py; _test_v1_multi_adjustment_undo.py; _test_v1_stems_multi_adjustment_undo.py; _test_v1_escape_navigation.py | Implementado y probado |
| Limpieza de intermedios de la sesión | Al salir de cada modo elimina solo archivos nuevos de la sesión; conserva masters aprobados y exportaciones vocales, y no elimina archivos preexistentes | _test_v1_safe_cleanup.py | Implementado; test de seguridad aislado |
| Validación audible con voces/canciones reales | No hay evidencia de una sesión de escucha real en los tests disponibles | No cubierta por la suite | Pendiente de prueba de aceptación con audio real; no bloquea la existencia de funciones, pero impide afirmar calidad audible certificada |

## Criterio de cierre
- “Implementado y probado” significa que la función existe y los tests listados pasaron; no implica garantía universal de calidad sonora.
- Autotune y corrección de pitch están excluidos de la aplicación activa V1/V2.
- Los ajustes de elementos individuales en una mezcla estéreo son aproximaciones espectrales, no separación de fuentes.
- La suite es sintética/automatizada; la prueba con voz real es una validación de calidad audible posterior.
- No se implementaron extras opcionales del ZIP (p. ej., receta por género, historial persistente, multibanda, dynamic EQ o preview corto) sin evidencia de que fueran requisitos V1.


## Verificación final de limpieza segura
La regresión consolidada posterior al ajuste de preservación de carpetas terminó con **22/22 pruebas aprobadas**, código de salida 0. Los intermedios preexistentes se conservan deliberadamente; la limpieza es por sesión y no borra retrospectivamente archivos antiguos.
