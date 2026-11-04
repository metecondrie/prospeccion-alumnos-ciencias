# Auditoría y pedido de cambios para Antigravity

**Proyecto:** `Prospeccion_Alumnos_Ciencias`
**Fecha de auditoría:** 2026-11-03
**Baseline verificado:** 39 registros en los tres artefactos (CSV fuente, CSV CRM y `RAW_DATA` del dashboard), 35 URLs únicas.
**Regla de trabajo:** no cambiar el diseño general ni el dataset sin aprobación. Resolver primero P0, después P1. Cada cambio debe incluir su prueba de aceptación.

---

## 0. Qué está bien y no hay que tocar

- El flujo central (copiar mensaje personalizado, abrir el anuncio y marcar estado) es la idea correcta.
- El diseño de tarjetas/tabla, los filtros por país y la persistencia en `localStorage` funcionan y se entienden.
- El CSV fuente está bien formado: UTF-8 con BOM, CRLF, 39 filas, comillas correctas.
- `Conclusiones_del_Proyecto.md` es la fuente de verdad más precisa: sus totales coinciden exactamente con los datos (17 AR, 9 ES, 7 CL, 2 MX, 2 CO, 2 PE; 35 online y 4 presenciales; 16/13/3/3/4 por materia).
- `directorio_plataformas.md` es sólido y accionable.
- No reemplazar la estética ni el stack sin pedido explícito.

---

## 1. P0 — bugs que rompen la función principal

### P0.1 — La plantilla por defecto no se personaliza

**Síntoma verificado:** al abrir `dashboard.html` con `localStorage` limpio, el banner muestra literalmente:

```
¡Hola{nombre_saludo}! ... clases particulares de {materia} (nivel {nivel}).
```

**Causa:** `DEFAULT_PITCH` (línea 340) usa llaves simples `{nombre_saludo}`, `{materia}` y `{nivel}`, pero todas las sustituciones buscan llaves dobles `{{nombre_saludo}}`, `{{materia}}` y `{{nivel}}` (líneas 428-430, 467-469, 479-481 y 500-504).

**Impacto:** en una instalación limpia, “Copiar Mensaje Maestro”, “Enviar Mensaje” y “Copiar Texto” copian las llaves crudas. La promesa central del dashboard no se cumple.

**Corrección:**
1. Cambiar en `DEFAULT_PITCH` las tres variables a doble llave: `{{nombre_saludo}}`, `{{materia}}`, `{{nivel}}`.
2. Migrar pitches ya guardados: si el texto guardado contiene `{nombre_saludo}` y no contiene `{{`, convertirlo a doble llave al leerlo.
3. Agregar un botón “Restaurar mensaje por defecto”.
4. Validar después de sustituir: si queda cualquier `{...}` o `{{...}}`, mostrar un aviso rojo en el banner y no copiar.

**Aceptación:**
- Con `localStorage` limpio, el banner muestra “¡Hola Bruno S.!” y “Ciencias Exactas”.
- Al hacer clic en “Enviar Mensaje” en cualquier lead, el portapapeles contiene nombre, materia y nivel resueltos, sin llaves.
- Un pitch guardado con llaves simples se migra sin perder el texto.

---

### P0.2 — Los IDs de lead colisionan

**Síntoma verificado:** `getLeadId()` (líneas 376-378) arma el ID como `plataforma + '_' + enlace`. Hay 35 IDs únicos para 39 leads y dos colisiones:

- 4 leads de Cronoshare Matemáticas comparten `Cronoshare_https://www.cronoshare.com/empleo/clases-particulares-matematicas`.
- 2 leads de Cronoshare Física comparten `Cronoshare_https://www.cronoshare.com/empleo/clases-particulares-fisica`.

**Impacto:** marcar un lead como “Contactado” marca a los otros 3 o al otro, sin aviso. Son 6 leads afectados.

**Corrección:**
1. Agregar un campo `id` estable a cada registro (por ejemplo `L001`…`L039`, o un slug de la URL cuando exista ID de aviso).
2. `getLeadId()` debe devolver `item.id` y, solo si falta, un fallback con hash de `plataforma + url + nombre + fecha + materia`.
3. Migrar los estados existentes: mapear el ID viejo al nuevo cuando sea inequívoco; si hay colisión, no adivinar: avisar y dejar los leads en “Pendiente”.
4. Al iniciar, validar que no haya IDs repetidos y mostrar un error visible si los hay.

**Aceptación:**
- 39 IDs únicos.
- Cambiar el estado de un lead de Cronoshare no cambia el de los demás.
- Los estados viejos se conservan cuando el mapeo es inequívoco.

---

### P0.3 — Los links de Cronoshare son páginas de categoría, no anuncios

**Síntoma verificado:** 7 de los 39 leads usan 4 URLs de categoría:

- `.../empleo/clases-particulares-matematicas` (4 leads)
- `.../empleo/clases-particulares-fisica` (2 leads)
- `.../empleo/clases-particulares-biologia` (1 lead)

No son fichas individuales: no identifican a la persona ni permiten un contacto directo. Además, Cronoshare requiere créditos para desbloquear el WhatsApp.

**Impacto:** el botón “Enviar Mensaje (Abrir & Copiar)” promete un contacto directo que en estos 7 casos no existe; además contribuye a la colisión de IDs del punto P0.2.

**Corrección (elegir una):**
- **A (mejor):** reemplazar cada URL por la ficha real de la solicitud, si el scrape original la tiene.
- **B (si no hay ficha):** conservar la URL, pero agregar `canal: "creditos"` y `enlace_tipo: "categoria"`, cambiar el CTA a “Abrir Cronoshare y buscar la solicitud” y no marcar “Contactado” automáticamente.
- **C:** separar estos 7 leads en una pestaña “Requieren créditos / sin link directo” y excluirlos del KPI de contacto directo.

**Aceptación:**
- Ningún lead muestra “Enviar Mensaje” como si fuera contacto directo cuando el link es de categoría.
- Los 7 leads tienen IDs distintos.
- El KPI distingue contacto directo de contacto con créditos.

---

### P0.4 — La documentación técnica está una fase atrás

**Síntoma verificado:** `DOCUMENTACION_TECNICA_PROYECTO.md` describe 43 registros; los archivos tienen 39. La diferencia es exactamente la que explica `Conclusiones`: 2 URLs de categoría de Colombia y 2 avisos duplicados de Belén M. (3 a 1). La doc quedó congelada antes de esa curaduría.

Errores concretos:

| Documento dice | Realidad verificada |
|---|---|
| 43 registros validados | 39 |
| Argentina 19, Colombia 4 | Argentina 17, Colombia 2 |
| Matemáticas 18, Física 15 | Matemáticas 16, Física 13 |
| Modalidad 100% online | 35 online y 4 presenciales |
| `RAW_DATA` con 43 registros | 39 |
| CSV con 8 columnas canónicas | 10 columnas |
| Planilla con Estado en columna H | En el CSV actual, Estado es columna J (la H es “Forma de Contacto”) |
| Tabla ordenable por columnas | No hay ordenamiento; solo se ordenan los países |
| Inventario de 6 scripts (`audit_with_llm.py`, `build_fancy_dashboard.py`, `create_dashboard.py`, `extract_*.py`, `common_filter.py`) | No existen en la carpeta ni en el Escritorio |
| Extracción de Reddit `r/UBA` y Workana | No hay registros de `r/UBA` ni de Workana |

**Corrección:**
1. Reescribir la doc con el baseline de 39 y la cadena 118 → 84 → 43 → 39, explicando las 4 bajas.
2. Corregir la tabla de métricas y la de columnas.
3. Quitar del inventario los scripts inexistentes o agregarlos si se recuperan de Drive. Si no aparecen, declarar “pipeline no reproducible” y pedir el crudo.
4. Implementar el ordenamiento por columnas o borrar esa afirmación.
5. Corregir el correo de `Conclusiones_del_Proyecto.md`: dice `contacto.docente@ciencias.org`; debe ser `contacto.docente@ciencias.org`.

**Aceptación:**
- `grep -c "43"` en la doc no devuelve referencias al dataset actual.
- Las cifras de la doc coinciden con un script de validación que se ejecuta antes de publicar.

---

## 2. P1 — datos, CRM y experiencia

### P1.1 — El filtro “Universitario” incluye preuniversitarios

**Verificado en el navegador:** al seleccionar “Universitario”, el dashboard muestra 22 de 39. Incluye 7 leads que son “Secundario / Pre-Universitario” o “Secundario / Pre-Universitario (PAES)”, porque el filtro usa `includes('universitario')` (línea 613).

**Corrección:** normalizar `nivel_categoria` a un valor cerrado (`Primaria`, `Secundario`, `Terciario`, `Universitario`, `Acceso`) y filtrar por igualdad. Mantener `nivel_detalle` para el texto libre.

**Aceptación:** “Universitario” devuelve 15 (o 16 si se decide incluir FP Superior), nunca 22.

### P1.2 — Faltan notas y seguimiento

El CSV CRM tiene columna “Notas / Teléfono”, pero el dashboard no tiene ningún campo de notas. Un CRM sin notas ni próximo paso no sirve para dar seguimiento.

**Agregar por lead:** `notas`, `telefono`, `precio`, `fecha_contacto`, `proximo_seguimiento`, `respondio` (sí/no), `canal_usado`.

**Aceptación:** se puede escribir una nota, guardarla, verla en la tarjeta y en la tabla, exportarla e importarla.

### P1.3 — El estado se pierde si se limpian los datos del navegador

Todo vive en `localStorage` (`alumnos_lead_statuses`, `alejo_master_pitch_v3`). No hay backup, importación ni restauración.

**Agregar:** “Exportar seguimiento (JSON)” y “Importar seguimiento (JSON)”, con versión de esquema. Avisar en la UI que limpiar datos del navegador borra el CRM.

**Aceptación:** exportar, borrar `localStorage`, importar y recuperar estados, notas y pitch.

### P1.4 — El CSV no es un respaldo fiel del dashboard

Hay 5 diferencias entre el CSV y `RAW_DATA`: el CSV mete la alerta dentro de `modalidad` y no tiene `alerta_modalidad`. Si se reconstruye el dashboard desde el CSV, se pierden las alertas y el filtro “Online” deja afuera el aviso de Euskera.

**Corrección:** un solo esquema canónico (ver sección 4). El CSV debe tener `alerta_modalidad` como columna propia y `modalidad` solo con `Online` / `Presencial` / `Mixta`.

**Aceptación:** `csv_a_json(csv) == RAW_DATA` campo por campo, incluidas las 5 alertas.

### P1.5 — Las fechas no sirven para priorizar

30 de 39 registros tienen `2026-11-01`. Es la fecha de captura, no la de publicación. Sin fecha real, la “ventana crítica de 15 minutos” no se puede usar.

**Corrección:** renombrar el campo a `fecha_captura` y agregar `fecha_publicacion` solo cuando se conozca. Mostrar en la UI “sin fecha real” en vez de una fecha engañosa.

**Aceptación:** ningún lead muestra una fecha de publicación inventada; se puede ordenar por captura y filtrar “sin fecha”.

### P1.6 — 16 de 39 no tienen nombre

El 41% usa saludo genérico. Está bien no inventar nombres, pero el pitch debería tener un fallback explícito (“Hola”) y no dejar `{nombre_saludo}` vacío entre signos.

**Aceptación:** con nombre vacío, el saludo es “¡Hola!”; con nombre, “¡Hola Bruno S.!”.

### P1.7 — Hay una persona duplicada y dos probables

- **Helena B. (Ñuñoa):** dos avisos que se complementan (“pack con Física” / “pack con Química”), mismos datos y IDs consecutivos. Es la misma persona: contactarla dos veces con el mismo pitch queda mal.
- **Rodrigo J. (Santiago):** dos avisos PAES (Matemáticas y Biología). Probable misma persona.
- **Lucas B., Diego M. y “Familia”** también se repiten, pero con ciudad o nivel distinto: probablemente son personas distintas. No agrupar sin verificar.

**Corrección:** agrupar por `persona_id` cuando coincidan nombre + ciudad + señales del aviso; mostrar “2 necesidades” en una sola tarjeta y un solo botón de contacto.

**Aceptación:** Helena B. aparece una vez con dos materias; no se le envía el mismo mensaje dos veces.

### P1.8 — El pitch no usa el tema específico

El directorio dice que nombrar el tema exacto mejora la respuesta, pero el dashboard solo interpola materia y nivel. Para Belén M. el mensaje dice “clases de Física” cuando el aviso es de Máquinas Hidráulicas; para el aviso de econometría dice “Matemáticas”.

**Corrección:** agregar `tema` y `{{tema}}` al pitch. Ejemplo: “vi tu búsqueda sobre Máquinas Hidráulicas (UADE)”.

**Aceptación:** cada lead tiene un `tema`; el mensaje copiado lo menciona.

### P1.9 — El pitch no tiene variantes por segmento

El mensaje por defecto dice “nivel universitario, secundario y técnico” y ofrece pizarra online. Eso no encaja con:

- 4 leads que piden presencial.
- 1 lead de primaria (7 años).
- 1 lead que pide Euskera.
- España, donde “recuperatorios” y “finales” suenan rioplatenses.

**Corrección:** variantes `online`, `presencial`, `primaria`, `espana`, `latam`, y una nota para Euskera. No mandar la variante “presencial” a quien pidió presencial sin reconocerlo.

**Aceptación:** el pitch presencial menciona “puedo darte la misma calidad online con pizarra digital”; el de primaria no promete nivel universitario; el de España usa “EBAU/selectividad” y evita “recuperatorio”.

### P1.10 — El botón marca “Contactado” antes de que envíes

`sendAndOpenLead()` copia, marca “Contactado” y abre la pestaña, aunque el copiado falle o cierres la pestaña sin escribir. No hay deshacer.

**Corrección:** marcar “Contactado” solo si el copiado tuvo éxito; agregar un toast con “Deshacer” y un estado intermedio “Preparado”.

**Aceptación:** si se cancela el copiado, el estado no cambia; el toast permite volver atrás.

### P1.11 — Seguridad de contenido scrapeado

El dashboard inserta `mensaje`, `nombre`, `plataforma` y `método` con `innerHTML` y arma `onclick` con interpolación de strings. Un aviso con `<img onerror=...>` o un nombre con apóstrofo puede ejecutar código o romper el botón. `window.open` tampoco valida el protocolo.

**Corrección:**
- Escapar HTML en todas las interpolaciones de datos.
- Reemplazar `onclick` inline por `data-*` + delegación de eventos.
- Validar que la URL sea `http:` o `https:` antes de abrir.
- Agregar `rel="noopener noreferrer"` al link de Google Sheets.

**Aceptación:** un nombre con `'` y un mensaje con `<script>` no rompen la UI ni ejecutan código.

### P1.12 — Banderas y header en Windows

Verificado en captura: las banderas se ven como “AR”, “ES”, “CL”, “MX”, “CO”, “PE”. Windows no tiene glifos de banderas; el emoji se renderiza como par de letras. A ~500 px, el header superpone el nombre “Alejo Ongaro” con el badge “18+ Años Docencia”.

**Corrección:** usar SVG de banderas o códigos de país; ajustar el header a `flex-wrap` o a un layout de dos filas por debajo de `sm`.

**Aceptación:** a 375 px y a 1440 px el header no se superpone; las banderas se ven iguales en Windows y Mac.

### P1.13 — Búsqueda sin acentos y sin orden

Buscar “Belén M.” no encuentra “Belén M.”; “Peru” no encuentra “Perú”. Además, no hay orden por fecha, urgencia ni estado, aunque la doc promete tabla ordenable.

**Corrección:** normalizar con `String.prototype.normalize('NFD').replace(/[\u0300-\u036f]/g, '')`; agregar orden por columna y un orden por defecto (urgencia y fecha de captura).

**Aceptación:** “Belén M.”, “Peru” y “Cordoba” encuentran sus leads; la tabla ordena por cualquier columna.

---

## 3. P2 — mejoras de producto

1. **KPIs que sumen:** agregar “En negociación”, “Descartado” y “Respondió”. Hoy “Contactados” mezcla contactado y negociación, y el total no coincide con la suma.
2. **Métricas de embudo:** tasa de respuesta, tasa de cierre, tiempo hasta el primer contacto y conversión por plataforma. Sin esto no se puede saber qué canal funciona.
3. **Fit score (0-100) y urgencia:** separar “es ciencias exactas” de “es un alumno”. 5 avisos son de temas afuera del alcance (Máquinas Hidráulicas, electrónica, anatomía, econometría, geometría descriptiva) y 3-4 no tienen verbo de demanda. No borrarlos: etiquetarlos y ordenar por fit.
4. **Chequeo de links:** script que verifique HTTP y marque `estado_anuncio` (`activo`, `vencido`, `desconocido`). Los clasificados caducan.
5. **Chequeo de duplicados:** validar IDs y personas al iniciar; mostrar un panel de advertencias.
6. **Cola de contacto:** vista “Para hoy” con fit × urgencia × frescura, para no recorrer 39 tarjetas.
7. **Google Sheets:** definir una sola fuente de verdad. Si el dashboard manda, escribir los estados a la planilla con Apps Script o un script de Python; si manda la planilla, importar desde ahí. Hoy el botón “Ver Google Sheets” parece sincronizado, pero no lo está.
8. **Offline real:** Tailwind por CDN y Google Fonts requieren internet; sin red el dashboard pierde estilos. Compilar el CSS y servirlo local, o aceptar explícitamente que es online.
9. **Separar archivos:** `data.js` (datos), `app.js` (lógica), `styles.css` (estilos). Sigue funcionando con doble clic y deja de ser un HTML de 70 KB con datos adentro.
10. **Pipeline reproducible:** `scripts/`, `requirements.txt`, `.env.example` con `GEMINI_API_KEY`, `run_pipeline.py` y `validate_dataset.py`. Si los scripts no aparecen, no inventarlos: documentar que no es reproducible y pedir el crudo.
11. **Auditoría de la IA:** guardar `descartados_por_ia.json` con el motivo por anuncio. Hoy no está; sin eso no se puede revisar por qué se descartó cada uno.
12. **Medir la precisión:** “100% de precisión” no es verificable sin muestra etiquetada. Etiquetar 30 anuncios a mano y reportar precisión con intervalo de confianza (Wilson). Mientras tanto, decir “39 prospectos curados manualmente”.
13. **Privacidad y cumplimiento:** no publicar la planilla con datos de alumnos; para menores, escribir al adulto responsable; no pedir datos personales al menor; revisar los términos de TusClases/Tablón/Milanuncios antes de automatizar; minimizar y borrar datos al cerrar la campaña.
14. **Automatización:** scraping diario, diff contra el día anterior y alerta por Telegram/email para los avisos nuevos. Es lo que realmente da la ventaja de 15 minutos.
15. **A/B del pitch:** guardar dos variantes y registrar cuál cerró. Sin medición, el “mensaje maestro” es una intuición.

---

## 4. Esquema canónico propuesto

Un solo registro por lead, con estos campos. El CSV fuente es la fuente de verdad; el dashboard se genera desde ahí.

```
id                  L001
plataforma          TusClases Argentina
canal               mensajeria | formulario | dm | creditos
nombre              Bruno S.
persona_id          P012          (para agrupar varios avisos de la misma persona)
materia             ["Matemáticas"]  (array normalizado)
tema                "Matemática 2 universitaria"
nivel_categoria     Universitario | Secundario | Terciario | Primaria | Acceso
nivel_detalle       "Universitario (CBC UBA)"
pais                Argentina
ciudad              Buenos Aires
modalidad           Online | Presencial | Mixta
alerta_modalidad    ""
idioma              es
urgencia            alta | media | baja
fit                 0-100
fecha_publicacion   2026-11-01  (solo si es real; si no, vacío)
fecha_captura       2026-11-03
estado_anuncio      activo | vencido | desconocido
mensaje             "Busco docente..."
metodo_contacto     "Mensajería interna..."
enlace              "https://..."
```

Y un registro de seguimiento separado, que es lo que hoy falta:

```
id, estado, fecha_contacto, proximo_seguimiento, respondio, notas, telefono, precio, canal_usado
```

Estados: `Pendiente`, `Preparado`, `Contactado`, `Respondió`, `En negociación`, `Cerrado`, `Descartado`.

---

## 5. Documentación a corregir

1. `DOCUMENTACION_TECNICA_PROYECTO.md`
   - 43 → 39; corregir todos los desgloses.
   - 100% online → 35 online / 4 presencial.
   - 8 columnas → 10; Estado H → J.
   - Quitar “ordenar por columnas” o implementarlo.
   - Quitar los 6 scripts inexistentes del inventario o agregarlos.
   - Explicar la cadena 118 → 84 → 43 → 39.
   - Agregar “Limitaciones”: fechas de captura, 41% sin nombre, 7 links de categoría, 5 temas fuera de alcance, precisión no medida.
2. `Conclusiones_del_Proyecto.md`
   - Corregir `contacto.docente@ciencias.org` → `contacto.docente@ciencias.org`.
   - Aclarar que los 39 son avisos, no necesariamente 39 personas (Helena B. tiene 2).
3. `directorio_plataformas.md`
   - Distinguir “regla 90/10” y “80% / 70%” como heurísticas internas, no como datos medidos.
4. Agregar un `README.md` con: qué es, cómo abrir el dashboard, dónde está la planilla, cómo se actualiza el dataset y cómo se hace backup.

---

## 6. Pruebas de aceptación (correr antes de entregar)

- [ ] Abrir `dashboard.html` con `localStorage` limpio: el banner no muestra llaves.
- [ ] Copiar el mensaje de un lead con nombre: contiene nombre, materia, nivel y tema; sin llaves.
- [ ] Copiar el mensaje de un lead sin nombre: dice “¡Hola!” y no deja espacios raros.
- [ ] Cambiar el estado de un lead de Cronoshare: los otros 6 no cambian.
- [ ] Filtrar “Universitario”: no aparecen “Pre-Universitario” ni PAES.
- [ ] Buscar “Belén M.”, “Peru”, “Cordoba”: encuentran sus leads.
- [ ] Exportar JSON, borrar `localStorage`, importar: se recuperan estados, notas y pitch.
- [ ] Exportar CSV y volver a generar el dashboard: los 39 registros y las 5 alertas son idénticos.
- [ ] Un nombre con apóstrofo y un mensaje con `<script>` no rompen la UI.
- [ ] A 375 px y 1440 px el header no se superpone.
- [ ] Todas las banderas se ven como banderas o como códigos, no como cuadros.
- [ ] `validate_dataset.py` reporta 39 registros, 39 IDs únicos, 35 URLs únicas y 5 alertas.

---

## 7. Prompt listo para pegar en Antigravity

```text
Sos Antigravity. Te paso una auditoría del proyecto Prospeccion_Alumnos_Ciencias.
Trabajá en este orden y no avances de fase sin dejar la anterior verificada.

Reglas:
- No cambies el diseño general ni el dataset sin aprobación.
- No borres registros: etiquetá, agrupá o marcá como descartado.
- No inventes scripts, métricas ni URLs que no estén en los archivos.
- Después de cada cambio, ejecutá las pruebas de aceptación de la sección 6.
- Actualizá la documentación en el mismo commit.

P0:
1. Corregir la plantilla: DEFAULT_PITCH usa llaves simples y las sustituciones buscan dobles. Migrar pitches guardados, agregar "Restaurar" y validar que no queden llaves.
2. Corregir los IDs: agregar id estable, migrar estados y validar duplicados. Hoy 4 leads de Cronoshare Matemáticas y 2 de Física comparten estado.
3. Resolver los 7 links de Cronoshare: si hay ficha real, reemplazarla; si no, marcar canal "creditos", cambiar el CTA y no auto-marcar Contactado.
4. Reescribir DOCUMENTACION_TECNICA con el baseline de 39 (no 43), 35 online/4 presencial, 10 columnas, Estado en J, y quitar los scripts y el ordenamiento inexistentes.

P1:
5. Normalizar nivel_categoria y arreglar el filtro "Universitario" (hoy devuelve 22, debe devolver 15/16).
6. Agregar notas, teléfono, precio, fecha de contacto, próximo seguimiento y respondió.
7. Agregar export/import JSON de estados, notas y pitch.
8. Unificar el esquema CSV/dashboard: alerta_modalidad como columna propia y modalidad solo Online/Presencial/Mixta.
9. Separar fecha_captura de fecha_publicacion; no mostrar fechas inventadas.
10. Agregar tema y {{tema}} al pitch; variantes presencial, primaria, España y LatAm.
11. Arreglar seguridad: escapar HTML, delegación de eventos, validar protocolo de URL, rel=noopener.
12. Arreglar banderas en Windows y header a 375 px.
13. Búsqueda sin acentos y orden por columna.

P2:
14. KPIs que sumen, métricas de respuesta/cierre, fit score, urgencia, cola "Para hoy".
15. Script de chequeo de links y de duplicados.
16. Separar data.js/app.js/styles.css y compilar Tailwind para uso offline.
17. Planificar sync con Google Sheets (una sola fuente de verdad) y backup.
18. Agregar README y validate_dataset.py.

Entregá un diff por punto, con la prueba que lo valida. Si algo no se puede hacer sin datos que faltan, decilo y pedí el insumo; no lo simules.
```

---

## 8. Anexo: evidencia rápida

- `dashboard.html`: 70.665 bytes; 39 registros embebidos; 35 URLs únicas; 5 alertas de modalidad.
- `alumnos_ciencias_exactas.csv`: 39 filas, 10 columnas, UTF-8 con BOM, CRLF.
- `dashboard_crm.csv`: 39 filas, 11 columnas, UTF-8 con BOM, CRLF.
- Muestra de 4 links (TusClases AR, Tablón, Reddit, Cronoshare): HTTP 200 al 2026-11-03.
- Consola del dashboard: solo el warning de Tailwind CDN (“should not be used in production”).
- Filtro “Universitario”: 22 resultados, 7 de ellos preuniversitarios.
- Fechas: 30 de 39 con `2026-11-01`.
- Nombres: 16 de 39 vacíos.
- Niveles: 24 textos distintos para 39 filas.
- Documentación: 43 vs 39; Argentina 19 vs 17; Colombia 4 vs 2; Matemáticas 18 vs 16; Física 15 vs 13.
