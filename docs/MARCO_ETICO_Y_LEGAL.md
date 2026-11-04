# Marco Ético, Legal y Protocolo de Protección de Datos

**Proyecto**: Pipeline de Prospección Educativa y CRM Local  
**Autor y Responsable Técnico**: Alejo Ongaro ([@metecondrie](https://github.com/metecondrie))  
**Última Actualización**: 4 de noviembre de 2026  

---

## 1. Declaración de Principios Éticos y Finalidad

Este software fue diseñado como una herramienta de apoyo pedagógico para docentes particulares de ciencias exactas. Su propósito exclusivo es conectar a profesionales de la enseñanza con estudiantes y familias que han publicado voluntariamente solicitudes de ayuda académica en portales clasificados de acceso público.

El sistema se rige bajo cuatro pilares éticos:
1. **Prospección No Invasiva**: No se realizan envíos salientes automatizados, campañas de spam ni difusión masiva.
2. **Intervención Humana Permanente (*Human-in-the-Loop*)**: Todo contacto con un estudiante o familia es evaluado, personalizado y ejecutado de forma directa por el docente a través de los canales autorizados por la plataforma de origen.
3. **Respeto a las Plataformas**: La recolección respeta los términos de acceso público, sin eludir controles de autenticación, muros de pago (*paywalls*) ni mecanismos CAPTCHA.
4. **Minimización y Anonimización de Datos**: El repositorio público no expone datos personales identificables (PII) de estudiantes.

---

## 2. Marco Normativo de Referencia

El tratamiento de datos del proyecto se alinea con los estándares de privacidad más exigentes a nivel internacional:

### A. Ley 25.326 de Protección de los Datos Personales (Argentina)
* **Datos de Fuentes de Acceso Público Irrestricto (Art. 5, Inc. 2.a):** La información procesada proviene de anuncios abiertos al público general en internet.
* **Principio de Calidad de los Datos (Art. 4):** Los datos son pertinentes y no excesivos para la finalidad de brindar clases particulares.
* **Consentimiento para el Fin Específico:** El titular del aviso ha manifestado explícitamente su voluntad de ser contactado por profesores de la materia solicitada.

### B. Reglamento General de Protección de Datos (RGPD / GDPR - UE 2016/679)
* **Minimización de Datos (Art. 5.1.c):** En este repositorio público, **todos los nombres reales y datos de contacto han sido completamente sustituidos por seudónimos sintéticos deterministas** mediante `scripts/anonymize_for_public.py`.
* **Interés Legítimo (Art. 6.1.f):** El contacto inicial se limita a responder a la petición directa formulada por el interesado en un portal público de empleo/clases.
* **Protección Especial a Menores:** Cuando un anuncio es formulado por un padre/madre para apoyo de su hijo/a menor de edad, el contacto se dirige invariablemente al adulto responsable anunciante.

---

## 3. Arquitectura del Centinela de Telegram: Escucha Pasiva y Cero Spam

Para despejar cualquier inquietud sobre el módulo en tiempo real (`scripts/telegram_centinela.py`):
1. **Modo Exclusivamente Pasivo (Event-Driven Listener):** El script escucha eventos entrantes (`events.NewMessage`) únicamente en grupos y comunidades públicas donde la cuenta ya es miembro participante.
2. **Cero Salidas Automatizadas (Zero-Outbound Spam):** El bot **nunca** envía mensajes privados (DMs) a los usuarios ni publica respuestas en los grupos. No existe riesgo de baneo por spam ni vulneración de la tranquilidad de los miembros.
3. **Alerta Privada al Docente:** La alerta de detección se remite exclusivamente al chat privado del docente, quien evalúa la pertinencia académica y responde de forma manual si corresponde.
4. **No Persistencia de @usernames:** El dataset canónico no guarda usuarios telefónicos de Telegram.

---

## 4. Política de Anonimización en el Repositorio de Portfolio

Para que este repositorio pueda exhibirse abiertamente como demostración técnica sin comprometer la privacidad de ninguna persona:
* Se diseñó y ejecutó un proceso de anonimización determinista in-place ([`scripts/anonymize_for_public.py`](file:///c:/Users/alele/Downloads/Nueva%20carpeta/scripts/anonymize_for_public.py)) con un pool cerrado de seudónimos con **0 colisiones** respecto a los nombres originales.
* Se eliminaron correos electrónicos personales, enlaces a hojas de cálculo privadas y rutas locales del sistema operativo.
* El pipeline cuenta con tests automatizados que bloquean el commit si se detecta cualquier nombre real residual.

---

## 5. Protocolo de Opt-Out y Derecho de Supresión

Si eres el autor de alguno de los anuncios públicos indexados en la muestra anonimizada y prefieres que sea retirado de inmediato del dataset de demostración:
* Escribe un correo a: `alejoongaro@gmail.com` o abre un issue en [GitHub Issues](https://github.com/metecondrie/prospeccion-alumnos-ciencias/issues).
* El registro será eliminado en menos de 24 horas hábiles sin necesidad de justificación alguna.
