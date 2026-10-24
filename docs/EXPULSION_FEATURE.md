# Nueva Intención: EXPULSION_INQUIRY

## Descripción General
Se ha agregado una nueva intención `EXPULSION_INQUIRY` al bot de WhatsApp para manejar consultas sobre órdenes de expulsión del país (administrativa o judicial).

## Características Implementadas

### 1. Clasificación de Intención
La IA detecta automáticamente cuando un usuario pregunta sobre expulsión mediante palabras clave:
- "expulsión"
- "orden de expulsión"
- "me expulsaron"
- "expulsión administrativa"
- "expulsión judicial"
- "SERMIG"
- "PDI"
- "tribunal penal"
- "deportación"
- "extranjería"

### 2. Flujo Conversacional (Árbol de Decisión)

El bot sigue un árbol de decisión para identificar el tipo de expulsión:

```
[Inicio: Usuario consulta por expulsión]
         |
         v
¿Tiene copia del documento o resolución?
    /              \
  (Sí)            (No)
   |               |
   v               v
¿Quién emite   ¿La persona está
el documento?  en un proceso penal?
   /    \           /      \
(SERMIG) (Tribunal) (Sí)   (No)
   |        |        |       |
   v        v        v       v
[Rama A] [Rama B] [Rama B] [Rama A]
```

#### Rama A: Expulsión Administrativa
- **Emisor**: SERMIG / Delegación Presidencial / PDI
- **Causa habitual**: Ingreso por paso no habilitado, vencimiento de visa, infracción a la Ley de Migraciones
- **Plazo de acción**: 5 días hábiles desde notificación
- **Recurso**: Recurso de Reclamación ante la Corte de Apelaciones
- **Efecto clave**: Presentar recurso suspende la ejecución de la medida
- **Prohibición de retorno**: 2 a 10 años según resolución

#### Rama B: Expulsión Judicial
- **Emisor**: Tribunal Penal / Juzgado de Garantía
- **Causa habitual**: Sustitución de pena privativa de libertad
- **Naturaleza**: Pena sustitutiva dictada por juez penal
- **Vía de impugnación**: Recurso penal en 5 a 10 días desde sentencia
- **Prohibición de retorno**: 10 años (si regresa antes, cumple condena en cárcel)

### 3. Respuesta Final

Cada rama incluye:
1. **Mensaje de texto detallado** con información legal específica
2. **Call-to-action**: Link de agendamiento (https://mediacionesrjz.cl/profesionales)
3. **Video explicativo**: Se envía automáticamente el video `expulsionrjz.mp4` ubicado en `D:\bot-jurico\web\frontend\public\expulsionrjz.mp4`

### 4. Persistencia de Contexto

El bot mantiene el contexto de la conversación en la base de datos para:
- Recordar las respuestas del usuario durante el flujo
- Evitar repetir preguntas si el usuario vuelve a consultar
- Identificar automáticamente el tipo de expulsión si se menciona explícitamente

## Archivos Modificados

### 1. `app/intents/definitions.py`
- Agregada intención `EXPULSION_INQUIRY`
- Agregados campos en `ExtractedIntent`:
  - `has_document`: bool
  - `document_issuer`: str (SERMIG/PDI/Tribunal)
  - `in_criminal_process`: bool
  - `expulsion_type`: str (administrativa/judicial)

### 2. `app/prompts/templates.py`
- Agregadas keywords de expulsión en el prompt de clasificación
- Agregados ejemplos de clasificación
- Agregada regla crítica #6 para detección de expulsión

### 3. `app/routers/webhook_legal_route.py`
- Implementada lógica completa de `Intent.EXPULSION_INQUIRY`
- Flujo conversacional con preguntas y respuestas
- Manejo de contexto persistente
- Respuestas específicas para Rama A y Rama B
- Inclusión de video en respuesta final

### 4. `app/whatsapp/gateway.py`
- Agregada función `send_video_with_caption()` para enviar videos por WhatsApp
- Timeout de 20 segundos para envío de videos
- Soporte para caption opcional

### 5. `app/routers/webhook.py`
- Agregada lógica para detectar y enviar videos cuando `query_result` incluye `video_url`
- El video se envía después del mensaje de texto

## Ejemplo de Conversación

```
Usuario: "Me llegó una orden de expulsión"

Bot: "📋 Para orientarte correctamente sobre tu caso de expulsión, necesito hacerte 
      algunas preguntas:
      
      ¿Tienes copia del documento o resolución de expulsión?
      
      Responde 'Sí' o 'No'"

Usuario: "Sí"

Bot: "👍 Perfecto. ¿Quién emite el documento?
      
      Responde:
      1️⃣ SERMIG / PDI (organismo administrativo)
      2️⃣ Tribunal (Juzgado de Garantía o Tribunal Penal)"

Usuario: "SERMIG"

Bot: "📋 EXPULSIÓN ADMINISTRATIVA
      
      Tipo identificado: Expulsión Administrativa
      
      📌 Causa habitual: Ingreso por paso no habilitado, vencimiento de visa o 
         infracción a la Ley de Migraciones
      
      ⏰ Plazo de acción: Dispones de 5 días hábiles desde la notificación para 
         interponer un Recurso de Reclamación ante la Corte de Apelaciones.
      
      ⚠️ Efecto clave: Presentar el recurso dentro del plazo suspende de inmediato 
         la ejecución de la medida hasta que la justicia resuelva.
      
      🚫 Prohibición de retorno: Se fija entre 2 y 10 años, según la resolución.
      
      ⚠️ El tiempo es crítico. Para revisar tu notificación, calcular el plazo 
         exacto y preparar la estrategia legal de suspensión, agenda una evaluación 
         directa con nuestros abogados especialistas.
      
      📅 Haz clic aquí para agendar y pagar tu consulta:
      https://mediacionesrjz.cl/profesionales
      
      🎥 Video explicativo sobre expulsión:
      https://mediacionesrjz.cl/expulsionrjz.mp4"

[El bot envía el video automáticamente]
```

## URLs de Recursos

- **Video de expulsión**: https://mediacionesrjz.cl/expulsionrjz.mp4
- **Link de agendamiento**: https://mediacionesrjz.cl/profesionales

## Notas Técnicas

1. **Manejo de Estado**: El flujo conversacional utiliza el campo `context` de la tabla `conversations` para mantener el estado entre mensajes.

2. **Detección Inteligente**: Si el usuario menciona explícitamente "expulsión administrativa" o "expulsión judicial", el bot salta directamente a la respuesta correspondiente sin hacer preguntas.

3. **Extracción de Entidades**: La IA puede extraer automáticamente:
   - Tipo de expulsión del mensaje inicial
   - Quién emitió el documento (SERMIG/PDI/Tribunal)
   - Si está en proceso penal

4. **Envío de Video**: El video se envía como mensaje separado después del texto, con un caption explicativo.

5. **Fallback**: Si el usuario no proporciona respuestas claras durante el flujo, el bot ofrece un mensaje general con el link de agendamiento.

## Próximas Mejoras Sugeridas

1. **Cálculo automático de plazos**: Permitir al usuario ingresar la fecha de notificación y calcular automáticamente los días restantes
2. **Documentos adjuntos**: Permitir que el usuario envíe foto de la resolución y extraer información mediante OCR
3. **Recordatorios**: Enviar recordatorios automáticos si el plazo está próximo a vencer
4. **Integración con CRM**: Registrar automáticamente casos de expulsión en el sistema CRM del estudio

## Testing

Para probar la nueva funcionalidad:

```bash
# Enviar mensaje de prueba al bot
"me llegó una orden de expulsión"
"tengo expulsión administrativa"
"SERMIG me notificó"
"tribunal me expulsó"
```

## Despliegue

Después de implementar estos cambios:

1. Reiniciar el servicio del bot
2. Verificar que el video esté accesible en la URL pública
3. Probar el flujo completo con un usuario de prueba
4. Monitorear logs para verificar que el video se envíe correctamente

---

**Fecha de implementación**: 8 de agosto de 2026  
**Desarrollador**: Kiro AI Assistant  
**Cliente**: Mediaciones RJZ (bot-jurico)
