# MixFlow V1 — contraste con paquete de referencia Claude
Fecha: 2026-10-09
Estado: documento de referencia solamente. NO autoriza implementar sugerencias ni modificar el código.

## 1. Cómo describe el paquete el flujo de Claude
El paquete no contiene código fuente de Claude ni demuestra acceso a su implementación interna. Describe un método de trabajo que se busca reproducir: **MEDIR → DECIDIR → PROCESAR → VOLVER A MEDIR**. Claude no “escucha” en este esquema; infiere propuestas a partir de mediciones y reglas. La escucha y decisión final pertenecen al usuario.

### Modo MEZCLA (un estéreo ya unido)
1. Analizar LUFS-I, LRA, true peak, crest factor, espectro y compatibilidad estéreo/fase.
2. Decidir correcciones moderadas a partir de resultados medidos, no usar una receta idéntica en todas las canciones.
3. Renderizar la cadena propuesta.
4. Volver a medir el archivo renderizado y corregir/reintentar si no cumple los límites.
5. Comparar el antes/después y entregar WAV de 24 bits.

Reglas iniciales descritas en el paquete: high-pass alrededor de 25–30 Hz solo si hay energía inútil; EQ correctiva amplia y moderada; compresión ligera solo si la dinámica lo justifica; evitar forzar el objetivo de loudness cuando requiere demasiada ganancia; true peak objetivo aproximado -1 dBTP.

### Modo STEMS
1. Cargar stems ya separados por el usuario; la app no separa fuentes.
2. Validar formato y sincronía; seleccionar/alinear la referencia.
3. Solo aquí, ofrecer afinación vocal opcional: detectar pitch/voicing, segmentar notas, proponer tonalidad/escala, aplicar intensidad 0–100%, preview y aceptación/rechazo.
4. Mezclar stems y después aplicar el mismo análisis/mastering adaptativo del modo MEZCLA.
5. Preguntar al final si se quieren exportar los stems vocales procesados por separado.

### Interacción común
- No destructivo: original en solo lectura y archivos nuevos por paso.
- Preview temporal; un preview rechazado no cambia el estado aceptado.
- A/B con volumen igualado.
- Progreso visible por fase.
- Historial por pasos con parámetros y rutas de entrada/salida; undo/redo por paso, sin reiniciar toda la sesión.
- En cambios de un paso anterior, volver a renderizar ese paso y los posteriores, no los pasos anteriores.
- La cadena y parámetros deben configurarse por género, no quedar todos fijos en el código.

## 2. Requisitos de base que hay que comprobar contra V1 (no son sugerencias nuevas)
- [x] Dos modos separados: MEZCLA y STEMS.
- [x] La afinación no debe aparecer en MEZCLA.
- [x] La app procesa stems ya separados; no añade separación de fuentes ni efectos creativos.
- [x] El análisis alimenta la receta adaptativa y la selección de loudness.
- [x] La voz puede afinarse por segmentos, con intensidad configurable y preview.
- [x] Preview pendiente no se acepta hasta aprobación; undo/rechazo probados en pruebas sintéticas.
- [x] Los originales se conservan.
- [ ] Historial persistente `historial.json` con puntero de pasos, parámetros y rutas; undo/redo verdadero por paso, incluido redo. El comportamiento probado actualmente reconstruye estados aceptados en memoria, pero no equivale a todo el historial persistente definido en el paquete.
- [ ] Previews de 10–15 segundos y limpieza automática al cerrar; el flujo actual genera previews de la mezcla completa, no el preview corto descrito en el paquete.
- [ ] A/B con loudness igualado. El menú permite escuchar/comparar archivos, pero no se ha demostrado una igualación automática de loudness para la comparación.
- [ ] Reglas de calidad finales explícitas y verificadas en la salida: LUFS dentro de tolerancia, true peak ≤ -1 dBTP y reintentos limitados. El normalizador tiene un bucle limitado, pero la puerta de calidad global descrita en el paquete no está cerrada como una verificación final inequívoca con informe de aprobado/reprobado.
- [ ] Configuración de receta por género. El ZIP incluye `parametros_por_genero.json`, pero hay que verificar que el código activo lo lea; no asumir que lo hace solo por existir el archivo.
- [ ] Progreso central por fases y por tarea larga, no solo mensajes de etapa.
- [ ] En STEMS, validar sample rate/longitud y sincronía de todos los stems de forma explícita antes de procesar; se probaron alineación y preservación de originales, pero no todas las combinaciones límite.

## 3. Lo que el código actual ya muestra, según inspección de V1
- El análisis previo muestra LUFS-I, LRA, true peak, RMS, peak, crest, DC, bandas espectrales y diagnóstico estéreo (correlación L/R, diferencia RMS, Side/Mid), regiones silenciosas y candidatos de transición energética.
- La receta adaptativa de MEZCLA es conservadora (high-pass, EQ fija condicionada a las proporciones espectrales, compresión condicionada por LRA/crest y corrección DC).
- El usuario puede escoger Light/Básico/Habitual/Alto/Personalizado/Sin cambios.
- Ajustes naturales de MEZCLA son ecualización selectiva aproximada del estéreo. No aíslan realmente voz, beat, adlibs ni backs; cualquier elemento que comparta las bandas afectadas puede cambiar.
- Se ejecutó la suite sintética de regresión con 21/21 pruebas aprobadas (2026-10-09). Esto demuestra comportamientos cubiertos por esas pruebas, no calidad audible con una canción real.

## 4. Elementos etiquetados como NUEVOS en el ZIP — conservar como sugerencias opcionales
**No se deben implementar ahora solo porque aparecen aquí.** El documento de modo MEZCLA los etiqueta como “NUEVO” o “Mejoras nuevas a añadir”:
- Mid/Side para mono en graves (alrededor de 100–120 Hz).
- Informe de clipping, fase, compatibilidad mono y silencios de inicio/final, más allá de las métricas ya presentes.
- A/B con loudness igualado.
- Soft clip antes del limitador.
- Compresión multibanda.
- EQ dinámico anti-aspereza.
- Puertas de calidad explícitas con reintentos.
Son propuestas del paquete; solo se tratarán como trabajo aprobado si el usuario lo pide expresamente o si se verifica que ya eran parte de los requisitos originales de V1 en otro material.

## 5. Parámetros de afinación del paquete para recuperar, no aplicar a ciegas
El ZIP sugiere pyin a 22.05 kHz, hop 512, rango C2–C6, confianza de voicing, padding ~75 ms, crossfade ~20 ms, preservación de formantes y preview de ~15 s. También menciona torchcrepe como alternativa opcional más pesada. Estos valores son orientativos en el ZIP; no los he cambiado en el código ni los doy por confirmados como decisiones originales de V1.

## 6. Próximo orden de trabajo
1. Mantener este contraste como referencia separada.
2. Revisar otros archivos originales/anteriores de V1 y material sobre el comportamiento de Claude, si existen, para distinguir requisitos confirmados de recomendaciones añadidas después.
3. Completar una matriz requisito → implementación actual → prueba/evidencia → estado.
4. Solo corregir un requisito original que falte o no funcione, con backup y regresión; dejar las sugerencias opcionales sin implementar.

**Nota de procedencia:** este documento se elaboró a partir de `pipeline_mastering_spec.zip` y de la inspección del `MixFlowAssistant.py` activo. No se cambió el código para añadir las sugerencias opcionales de la sección 4.

## 7. Contraste adicional de detalles concretos (inspección del código activo)
- [ ] `parametros_por_genero.json`: no se encontró en la carpeta del proyecto donde está `MixFlowAssistant.py`; además, el código inspeccionado no carga este archivo. Por tanto, los valores de ejemplo del ZIP no están conectados a la receta activa.
- [ ] `historial.json`: no se encontró junto al código y los historiales actuales son listas en memoria durante la sesión; no existe evidencia de persistencia/reanudación o redo tras cerrar.
- [ ] Afinación: el código activo usa el pico FFT predominante entre 70–1000 Hz, no `librosa.pyin`; procesa bloques fijos de 20 s. No se observa detector de voicing por frame, segmentación por nota estable, padding/crossfade entre segmentos ni opción explícita de preservación de formantes. Es una diferencia importante respecto al método descrito en el ZIP y debe contrastarse con los requisitos originales del V1 antes de corregirse.
- [ ] El ZIP describe una preview de 10–15 s para la afinación y previews temporales para efectos en ambos modos. El flujo actual de afinación renderiza los segmentos completos de los stems seleccionados y el preview general de mezcla se procesa en duración completa; no es el preview corto descrito.
- [x] La corrección por segmentos y la elección manual de distintos destinos por tramos sí existen, pero los tramos son de 20 s fijos y cada tramo usa una detección predominante. No debe confundirse con la segmentación por nota estable propuesta en el ZIP.
- [x] La cadena de MEZCLA se construye desde el original en cada preview, con ajustes aceptados acumulados; no se apilan efectos encima del WAV degradado anterior. Esta parte sí coincide con la lógica incremental de feedback descrita por el usuario.
- [ ] No se debe presentar la referencia al “comportamiento de Claude” como una ingeniería inversa confirmada. El ZIP explica un pipeline deseado y aclara que Claude decide a partir de métricas; no contiene logs ni trazas verificables de Claude. Sirve como especificación de referencia, no como prueba de lo que Claude hizo en una sesión concreta.


## 8. Aclaraciones del usuario: análisis adaptativo, género e historial de previews (2026-10-09)
- [x] Parámetros por género: no se consideran requisito confirmado ni sustituto del análisis. El usuario señala correctamente que no existe una receta universal por género y que el tratamiento depende de la grabación concreta (voz, micrófono, ambiente, balance y mediciones). El análisis existente de LUFS y demás métricas debe alimentar las decisiones adaptativas. Mantener el archivo de género del ZIP como referencia opcional; no implementarlo sin evidencia adicional de que era requisito original.
- [x] Historial persistente entre sesiones: baja prioridad y posiblemente una interpretación errónea del término «historial». La hipótesis alternativa es que el documento se refería a previews temporales que se eliminan automáticamente para no obligar al usuario a borrarlos manualmente. No tratar `historial.json` como requisito confirmado. Verificar gestión y limpieza de previews temporales en el código.
- [x] Afinación por segmentos: el usuario confirma que ya se había especificado que un mismo stem puede cambiar de nota/tonalidad hacia el final. Esto es un requisito previo de V1, no una función nueva. La diferencia pendiente es técnica: comprobar si el método actual basado en picos FFT y bloques fijos de 20 s detecta y corrige esos cambios con precisión suficiente. No sustituir el requisito por segmentación fija sin validar.


### 8.1 Verificación del código: previews temporales
- [x] Inspeccionadas las referencias de `MixFlowAssistant.py` a previews, directorios temporales y limpieza.
- [x] MEZCLA guarda los renders en `MixFlow_Output/Mezcla/<nombre>`; STEMS guarda los renders en `MixFlow_Output/Stems/<nombre>`.
- [x] Los nombres de previews, renders de afinación y estados de ajuste se escriben en esos directorios persistentes.
- [x] No se encontró uso de `TemporaryDirectory`, `tempfile` ni una limpieza general de previews al cerrar/cancelar en el código inspeccionado.
- [!] Esto confirma acumulación potencial de previews, pero no prueba por sí solo que la palabra «historial» del ZIP se refiriera a ellos. La interpretación de previews temporales es una hipótesis plausible del usuario.
- [ ] Pendiente de diseñar/verificar limpieza segura: conservar siempre el máster final aprobado y los originales; eliminar únicamente previews y renders intermedios al cerrar o cancelar. No modificar código todavía hasta revisar los puntos de salida y los tests que puedan depender de esos archivos.


### 8.2 Verificación técnica de afinación por segmentos (hecha, no solo pendiente)
- [x] Inspección de `choose_tune_plan()`: pregunta explícitamente si la nota destino cambia por secciones; permite introducir una nota destino distinta para cada tramo.
- [x] Inspección de `pitch_segments()` y `tune_stem()`: divide actualmente el audio en bloques fijos de 20 s, estima una nota por bloque y procesa cada bloque con su objetivo correspondiente.
- [x] Ejecutado `_test_v1_pitch_segments.py`: PASS. Confirma que se guardan distintos objetivos por tramo y se respeta la intensidad seleccionada.
- [x] Ejecutado `_test_v1_tune_render_segments.py`: PASS. Audio sintético de 40 s (220 Hz y luego 440 Hz) se detecta como A3 y A4 en los dos bloques y el render conserva la duración.
- [!] Límite confirmado: esto verifica el mecanismo de bloques y objetivos distintos, no una afinación automática precisa por cada nota dentro de una frase. La segmentación es fija cada 20 s, y `detect_pitch()` usa el pico FFT predominante entre 70 y 1000 Hz; puede confundir armónicos y no demuestra que detecte bien voces reales con acompañamiento, vibrato, consonantes o cambios dentro de un bloque de 20 s.
- [x] Conclusión: el requisito original de permitir notas distintas dentro de un mismo stem sí está parcialmente implementado y las pruebas sintéticas pasan. No debe etiquetarse como función totalmente terminada en calidad real: queda por validar con voz real y comprobar el requisito exacto de detección/corrección segmentada que se definió originalmente. No se modificó el código.


### 8.3 Verificación técnica del análisis adaptativo de MEZCLA (2026-10-09)
- [x] `MixFlowAnalyzer.analyze()` calcula LUFS/TP/LRA mediante FFmpeg loudnorm; RMS, pico, crest factor y DC; distribución espectral por bandas; diagnósticos de muestras cercanas a escala completa, correlación L/R, Side/Mid, regiones silenciosas y cambios candidatos de energía en ventanas de 3 s.
- [x] `adaptive_mix_filters()` sí consume mediciones reales del archivo para decidir filtros: proporciones espectrales de graves/graves-medios/presencia/aire activan EQ condicional; LRA y crest activan compresión conservadora; DC activa corrección DC. La receta no depende de un género.
- [x] `recommend_loudness()` usa LUFS-I, true peak, LRA y crest para proponer una de las etiquetas de loudness; el usuario puede aceptar la sugerencia, elegir otra o definir un objetivo personalizado.
- [x] `_test_v1_adaptive_recipe.py` comprueba una señal sintética con graves dominantes/dinámica alta y una equilibrada: en la primera activa las correcciones esperadas; en la segunda deja únicamente el high-pass de 28 Hz. `_test_v1_loudness_recommendation.py` comprueba casos de recomendación. Los tests específicos constan como existentes; no se repitieron en esta inspección.
- [!] Límite importante: las bandas son proporciones globales del espectro y los umbrales son reglas fijas, no una evaluación semántica que identifique por separado voz/beat/adlibs en una mezcla estéreo. El feedback de subir/bajar esos elementos usa filtros espectrales aproximados, no separación de fuentes. El análisis mide más cosas de las que actualmente influyen en la receta; por ejemplo, la correlación L/R y los indicadores de clipping se muestran como diagnóstico pero no activan por sí mismos una corrección automática.
- [x] Conclusión: el núcleo adaptativo existe y usa mediciones reales; no es una receta fija por género. Queda pendiente comprobar con casos de audio variados que los umbrales y la intensidad de los ajustes sean adecuados, sin añadir las mejoras opcionales del ZIP.

### 8.4 Confirmación del ciclo de archivos temporales
- [x] La inspección del árbol `MixFlow_Output` encontró WAV intermedios persistentes (`*_base.wav`, `*_SELECTIVE_*.wav`, `*_PREVIEW.wav`, `*_LOUD.wav`, `*_loudwork_*.wav`, renders de afinación y archivos de rechazo/undo) junto con masters finales.
- [!] Por tanto, la acumulación no es solo teórica: se guardan decenas de WAV en carpetas de salida. No se borró nada en esta auditoría porque hay que separar con seguridad archivos de prueba, intermedios y entregables finales; la limpieza indiscriminada podría eliminar un master válido.
- [ ] Próximo paso seguro: definir una limpieza por sesión que borre solo los intermedios creados en esa ejecución, conserve originales y masters aprobados, y tenga pruebas para aceptación, cancelación y error. No se implementó todavía.
