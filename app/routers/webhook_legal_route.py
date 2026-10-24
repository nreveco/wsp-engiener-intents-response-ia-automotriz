"""
Función _route_intent para estudio jurídico.
Este archivo reemplaza la lógica de routing del webhook.py original.
"""

from app.config import settings
from app.db.models import Business, BusinessSettings, Conversation
from app.intents.definitions import Intent
from app.services import bookings, handoff, leads, notifications, quotes
from app.services import legal_services, case_inquiries, fee_info
from app.whatsapp.gateway import send_text_message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import attributes
import logging

logger = logging.getLogger(__name__)


def clean_expulsion_flow_context(context: dict, conversation) -> dict:
    """
    Limpia todas las keys del flujo de expulsión del contexto.
    Esto permite que el usuario pueda iniciar una nueva conversación después de completar el flujo.
    """
    logger.info("🧹 Limpiando contexto del flujo de expulsión - flujo completado")
    
    # Limpiar todas las keys del flujo
    context.pop("expulsion_flow_started", None)
    context.pop("awaiting_document_confirmation", None)
    context.pop("awaiting_document_issuer", None)
    context.pop("awaiting_criminal_process", None)
    context.pop("expulsion_type", None)
    context.pop("has_document", None)
    context.pop("document_issuer", None)
    context.pop("in_criminal_process", None)
    
    # Actualizar el contexto en la conversación
    conversation.context = context
    
    # Marcar como modificado para SQLAlchemy
    attributes.flag_modified(conversation, "context")
    
    logger.info("✅ Contexto limpiado - usuario puede iniciar nueva conversación")
    
    return context


async def _route_intent_legal(
    intent: Intent,
    extracted,
    business: Business,
    biz_settings,
    db: AsyncSession,
    customer_phone: str,
    customer_name: str,
    conversation: Conversation,
    currency_symbol: str,
    phone_number_id: str,
    message_text: str,
) -> tuple[dict, bool]:
    """
    Router de intenciones para estudio jurídico.
    Retorna (query_result, interactive_sent).
    """
    wa_token = settings.whatsapp_token
    
    # ----------------------------------------------------------
    # VERIFICAR SI ESTÁ ESPERANDO CONTEXTO PARA HANDOFF
    # ----------------------------------------------------------
    context = conversation.context or {}
    
    # ⚠️ CRÍTICO: Si estamos en medio de un flujo de expulsión, mantener el contexto
    # incluso si la intención no se detecta correctamente
    in_expulsion_flow = (
        context.get("expulsion_flow_started") and 
        (context.get("awaiting_document_confirmation") or 
         context.get("awaiting_document_issuer") or 
         context.get("awaiting_criminal_process"))
    )
    
    # 🔄 RESET: Si el usuario dice GREETING, THANKS o HUMAN_SUPPORT, limpiar el flujo de expulsión
    reset_intents = [Intent.GREETING, Intent.THANKS, Intent.HUMAN_SUPPORT]
    if intent in reset_intents and in_expulsion_flow:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"🔄 RESET: Usuario cambió de tema (intent={intent.value}) - limpiando flujo de expulsión"
        )
        
        # Limpiar todas las keys del flujo de expulsión
        context.pop("expulsion_flow_started", None)
        context.pop("awaiting_document_confirmation", None)
        context.pop("awaiting_document_issuer", None)
        context.pop("awaiting_criminal_process", None)
        context.pop("expulsion_type", None)
        context.pop("has_document", None)
        context.pop("document_issuer", None)
        context.pop("in_criminal_process", None)
        
        conversation.context = context
        
        # 🔧 CRÍTICO: Marcar el campo context como modificado
        from sqlalchemy.orm import attributes
        attributes.flag_modified(conversation, "context")
        
        await db.commit()
        
        in_expulsion_flow = False  # Ya no está en flujo
        
        logger.info(
            f"✅ Contexto limpiado - usuario puede iniciar nueva conversación"
        )
    
    # Si está en flujo de expulsión (y NO fue reseteado), forzar la intención a EXPULSION_INQUIRY
    if in_expulsion_flow:
        intent = Intent.EXPULSION_INQUIRY
    
    if context.get("awaiting_handoff_context") and intent not in [Intent.HUMAN_SUPPORT, Intent.THANKS]:
        # Usuario está respondiendo con el contexto para el handoff
        context["handoff_context"] = message_text
        context["awaiting_handoff_context"] = False
        conversation.context = context
        await db.commit()
        
        # Ahora proceder con el handoff real
        result = await handoff.request_human_handoff(
            db=db,
            conversation_id=conversation.id,
            human_support_phone=business.human_support_phone or "",
        )
        
        if business.human_support_phone:
            urgency_note = ""
            if extracted.is_detained or extracted.urgency == "high":
                urgency_note = " 🚨 URGENTE - Cliente detenido o situación crítica"
            
            full_context = f"Contexto del cliente: {message_text}{urgency_note}"
            
            await notifications.notify_handoff(
                whatsapp_token=wa_token,
                phone_number_id=phone_number_id,
                owner_phone=business.human_support_phone,
                customer_phone=customer_phone,
                customer_name=customer_name,
                last_message=full_context,
            )
        
        return result, False

    # ----------------------------------------------------------
    # INTENCIONES MANTENIDAS (útiles para estudio jurídico)
    # ----------------------------------------------------------

    if intent == Intent.GREETING:
        # Mensaje de bienvenida con logo
        welcome_caption = (
            f"¡Bienvenido/a a *{business.name}*! 👉\n\n"
            f"Somos un centro especializado en *Mediación Familiar* y asesoría jurídica integral.\n\n"
            f"👉 *Nuestras áreas de especialización:*\n"
            f"    Mediación Familiar (VIF, custodia, pensiones)\n"
            f"    Derecho de Familia\n"
            f"    Derecho Civil\n"
            f"    Derecho Penal\n"
            f"    Consultoría Tributaria\n\n"
            f"Estamos aquí para orientarte y brindarte la mejor solución legal.\n\n"
            f"¿En qué podemos asesorarte hoy? 👉"
        )
        
        # Logo publico desde el frontend (ruta public accesible sin autenticacion)
        logo_url = "https://mediacionesrjz.cl/logo.jpg"
        
        return {
            "greeting_with_image": True,
            "image_url": logo_url,
            "caption": welcome_caption
        }, False

    elif intent == Intent.THANKS:
        # Agradecimiento o despedida - mensaje de cierre
        return {
            "default_message": (
                "¡De nada! 👉 Fue un gusto ayudarte. "
                "Si necesitas algo más adelante, aquí estaremos para asesorarte. "
                "¡Que tengas un excelente día! 👉👉"
            )
        }, False

    elif intent == Intent.BOOKING:
        # Agendar consulta con abogado - Enviar URL de agendamiento directo
        booking_url = "https://mediacionesrjz.cl/profesionales"
        
        msg = (
            f"👉 Perfecto, puedes agendar tu sesión directamente aquí:\n\n"
            f"👉 {booking_url}\n\n"
            f"En el link podrás:\n"
            f"? Elegir al profesional que prefieras\n"
            f"? Ver horarios disponibles\n"
            f"? Seleccionar fecha y hora\n"
            f"? Ver el valor de la sesión\n"
            f"? Realizar el pago online\n\n"
            f"Si tienes alguna duda o necesitas ayuda con el agendamiento, no dudes en escribirnos. 👉"
        )
        
        return {"default_message": msg}, False

    elif intent == Intent.QUOTE_REQUEST:
        # Solicitar presupuesto personalizado
        description = (
            extracted.quote_description
            or extracted.description
            or extracted.legal_matter
            or extracted.service
            or message_text
        )
        result = await quotes.create_quote_request(
            db=db,
            business_id=business.id,
            customer_phone=customer_phone,
            description=description,
            customer_name=customer_name,
        )
        if result.get("success") and business.human_support_phone:
            data = result["data"]
            await notifications.notify_new_quote(
                whatsapp_token=wa_token,
                phone_number_id=phone_number_id,
                owner_phone=business.human_support_phone,
                quote_id=data["quote_id"],
                customer_phone=customer_phone,
                customer_name=customer_name,
                description=description,
            )
        return result, False

    elif intent == Intent.HOURS_QUERY:
        # Horarios de atención
        if biz_settings and biz_settings.hours:
            return {"data": {"horarios": biz_settings.hours}}, False
        return {"default_message": "Nuestro horario es de lunes a viernes de 9:00 a 18:00, sábados de 10:00 a 14:00. 👉"}, False

    elif intent == Intent.LOCATION_QUERY:
        # Dirección de la oficina
        if biz_settings and biz_settings.address:
            msg = f"👉 *Dirección:* {biz_settings.address}"
            if biz_settings.city:
                msg += f", {biz_settings.city}"
            if biz_settings.maps_url:
                msg += f"\n👉? Google Maps: {biz_settings.maps_url}"
            return {"data": {"address": biz_settings.address}, "default_message": msg}, False
        return {"default_message": "👉 Escríbenos y te enviamos la dirección exacta de nuestra oficina."}, False

    elif intent == Intent.HUMAN_SUPPORT:
        # 👉 CRÍTICO: Derivar a abogado humano
        # Ofrecer 2 opciones: agendar consulta o número directo para urgencias
        
        # Si está detenido o es urgente, dar número directo inmediatamente
        if extracted.is_detained or extracted.urgency == "high":
            urgency_note = " 👉 URGENTE - Cliente detenido o situación crítica"
            
            # Notificar inmediatamente al abogado
            if business.human_support_phone:
                await notifications.notify_handoff(
                    whatsapp_token=wa_token,
                    phone_number_id=phone_number_id,
                    owner_phone=business.human_support_phone,
                    customer_phone=customer_phone,
                    customer_name=customer_name,
                    last_message=f"{message_text}{urgency_note}",
                )
            
            # Dar número directo para casos urgentes
            return {
                "default_message": (
                    f"� Entiendo que tu situación es urgente. Para casos como el tuyo, te recomiendo contactar directamente a nuestro abogado:\n\n"
                    f"� *Número directo*: +56975152417\n\n"
                    f"Disponible para emergencias legales. También puedes agendar una consulta formal aquí: https://mediacionesrjz.cl/profesionales"
                )
            }, False
        
        # Para casos no urgentes, ofrecer ambas opciones
        return {
            "default_message": (
                "Entiendo que necesitas hablar con un abogado. �‍⚖️ Tienes 2 opciones:\n\n"
                "1️⃣ *Agendar una consulta*\n"
                "� Puedes reservar una hora aquí: https://mediacionesrjz.cl/profesionales\n"
                "Ver horarios disponibles, valores y realizar el pago online.\n\n"
                "2️⃣ *Contacto directo* (solo para casos urgentes difíciles de resolver por chat)\n"
                "� Llama al: +56975152417\n\n"
                "¿Qué opción prefieres? �"
            )
        }, False

    # ----------------------------------------------------------
    # NUEVAS INTENCIONES LEGALES
    # ----------------------------------------------------------

    elif intent == Intent.CASE_INQUIRY:
        # Cliente consulta si pueden ayudarlo con su caso
        legal_area = extracted.legal_area
        legal_matter = extracted.legal_matter
        description = extracted.description or message_text
        urgency = extracted.urgency or "medium"
        is_detained = extracted.is_detained or False
        
        # Crear consulta de caso
        inquiry = await case_inquiries.create_case_inquiry(
            db=db,
            business_id=business.id,
            customer_phone=customer_phone,
            customer_name=customer_name,
            legal_area=legal_area,
            legal_matter=legal_matter,
            description=description,
            urgency=urgency,
            is_detained=is_detained,
            has_prior_record=extracted.has_prior_record,
            benefit_type=extracted.benefit_type,
        )
        
        # Si es urgente o está detenido, notificar inmediatamente
        if urgency == "high" or is_detained:
            await case_inquiries.notify_urgent_case(
                db=db,
                inquiry_id=inquiry["id"],
                business_id=business.id,
            )
        
        # Buscar servicios relacionados si hay asunto legal
        services_data = []
        if legal_matter:
            services = await legal_services.get_services_by_legal_matter(
                db=db,
                business_id=business.id,
                legal_matter=legal_matter,
                limit=3
            )
            services_data = services
        
        return {
            "data": {
                "inquiry": inquiry,
                "services": services_data,
                "is_urgent": urgency == "high" or is_detained
            }
        }, False

    elif intent == Intent.SERVICE_INFO:
        # Cliente pregunta por información de servicios legales
        # Retornar información completa de servicios con precios
        services_info = {
            "services": [
                {
                    "name": "Consulta Penal",
                    "area": "Derecho Penal",
                    "description": "Consulta en materia penal",
                    "duration": "30 minutos",
                    "price": "$10,000",
                    "status": "Disponible"
                },
                {
                    "name": "Consulta de Familia",
                    "area": "Derecho de Familia",
                    "description": "Orientación legal en derecho de familia",
                    "duration": "30 minutos",
                    "price": "$15,000",
                    "status": "Disponible"
                },
                {
                    "name": "Consulta Civil",
                    "area": "Derecho Civil",
                    "description": "Asesoría en contratos, demandas y asuntos civiles",
                    "duration": "30 minutos",
                    "price": "$30,000",
                    "status": "Disponible"
                },
                {
                    "name": "Consulta Tributaria",
                    "area": "Derecho Civil",
                    "description": "Asesoría en impuestos, fiscalización y planificación tributaria",
                    "duration": "60 minutos",
                    "price": "$50,000",
                    "status": "Disponible"
                },
                {
                    "name": "Consulta orden de Expulsión",
                    "area": "Derecho Migratorio",
                    "description": "Asesoría especializada en casos de expulsión administrativa o judicial",
                    "duration": "40 minutos",
                    "price": "Consultar",
                    "status": "Disponible"
                },
                {
                    "name": "Peritaje contable",
                    "area": "Derecho Comercial",
                    "description": "Peritajes contables y financieros para procesos judiciales, requiere evaluación sin costo",
                    "duration": "30 minutos",
                    "price": "Sin costo (evaluación)",
                    "status": "Disponible"
                },
                {
                    "name": "Peritaje social",
                    "area": "Derecho Comercial",
                    "description": "Peritajes sociales para procesos judiciales",
                    "duration": "240 minutos",
                    "price": "$500,000",
                    "status": "Disponible"
                }
            ]
        }
        
        return {"data": services_info}, False

    elif intent == Intent.PAYMENT_INFO:
        # Cliente pregunta por honorarios y precios de servicios
        services_pricing = {
            "services": [
                {"name": "Consulta Penal", "price": "$10,000", "duration": "30 minutos"},
                {"name": "Consulta de Familia", "price": "$15,000", "duration": "30 minutos"},
                {"name": "Consulta Civil", "price": "$30,000", "duration": "30 minutos"},
                {"name": "Consulta Tributaria", "price": "$50,000", "duration": "60 minutos"},
                {"name": "Consulta orden de Expulsión", "price": "Consultar", "duration": "40 minutos"},
                {"name": "Peritaje contable", "price": "Evaluación sin costo", "duration": "30 minutos"},
                {"name": "Peritaje social", "price": "$500,000", "duration": "240 minutos"}
            ],
            "payment_methods": "transferencia, efectivo",
            "has_payment_plans": True
        }
        
        return {"data": services_pricing}, False

    elif intent == Intent.TIMEFRAME_QUERY:
        # Cliente pregunta cuánto demora un proceso
        legal_matter = extracted.legal_matter
        
        if legal_matter:
            # Buscar servicio específico con timeframe
            services = await legal_services.get_services_by_legal_matter(
                db=db,
                business_id=business.id,
                legal_matter=legal_matter,
                limit=1
            )
            if services and services[0].get("estimated_timeframe"):
                timeframe = services[0]["estimated_timeframe"]
                return {
                    "data": {"timeframe": timeframe, "service": services[0]["name"]},
                    "default_message": f"👉 El proceso de {services[0]['name']} generalmente toma {timeframe}. Esta es información general. Los plazos pueden variar según las particularidades de cada caso. 👉"
                }, False
        
        return {
            "default_message": (
                "👉 Los plazos de los procesos legales varían según el tipo de caso y su complejidad. "
                "Para darte una estimación precisa, necesitamos evaluar tu situación específica. "
                "¿Te gustaría agendar una consulta gratuita? 👉"
            )
        }, False

    elif intent == Intent.LAWYER_IDENTITY:
        # Cliente pregunta con quién habla
        return {
            "default_message": (
                f"👉👉? Soy el asistente virtual de *{business.name}*. "
                "Estoy aquí para responder tus consultas iniciales y coordinar tu atención con nuestro equipo de abogados. "
                "¿En qué más puedo ayudarte? 👉"
            )
        }, False

    elif intent == Intent.BENEFIT_INFO:
        # Cliente pregunta por beneficios penitenciarios
        benefit_type = extracted.benefit_type or "beneficios penitenciarios"
        
        return {
            "data": {"benefit_type": benefit_type},
            "default_message": (
                f"👉 Los {benefit_type} dependen de varios factores como el tipo de delito, "
                "tiempo cumplido, conducta, antecedentes, entre otros. Esta es información general. "
                "Para evaluar si calificas y asesorarte en el proceso, necesitamos revisar tu caso específico. "
                "¿Te gustaría agendar una consulta con nuestro abogado? 👉"
            )
        }, False

    elif intent == Intent.PRIOR_RECORD_QUERY:
        # Cliente pregunta qué pasa con sus antecedentes previos
        return {
            "default_message": (
                "👉 Tener antecedentes previos puede influir en la estrategia de defensa y las salidas alternativas disponibles, "
                "pero cada caso es único. Necesitamos evaluar tu situación completa para darte una orientación precisa. "
                "Esta es información general. ¿Quieres agendar una consulta para revisar tu caso en detalle? 👉"
            )
        }, False

    elif intent == Intent.EXPULSION_INQUIRY:
        # ----------------------------------------------------------
        # NUEVA INTENCIÓN: EXPULSIÓN (ADMINISTRATIVA O JUDICIAL)
        # ----------------------------------------------------------
        
        # Verificar si ya tenemos información en el contexto de conversación
        context = conversation.context or {}
        
        # Si ya sabemos el tipo de expulsión, dar respuesta específica
        if extracted.expulsion_type == "administrativa" or context.get("expulsion_type") == "administrativa":
            # RAMA A: Expulsión Administrativa (SERMIG/PDI)
            video_url = "https://mediacionesrjz.cl/expulsionrjz.mp4"
            
            msg = (
                "⚖️ *EXPULSIÓN ADMINISTRATIVA*\n\n"
                "*Tipo identificado:* Expulsión Administrativa\n\n"
                "📋 *Causa habitual:* Ingreso por paso no habilitado, vencimiento de visa o infracción a la Ley de Migraciones\n\n"
                "⏰ *Plazo de acción:* Dispones de *5 días hábiles* desde la notificación para interponer un Recurso de Reclamación ante la Corte de Apelaciones.\n\n"
                "🛡️ *Efecto clave:* Presentar el recurso dentro del plazo suspende de inmediato la ejecución de la medida hasta que la justicia resuelva.\n\n"
                "🚫 *Prohibición de retorno:* Se fija entre *2 y 10 años*, según la resolución.\n\n"
                "⚠️ *El tiempo es crítico.* Para revisar tu notificación, calcular el plazo exacto y preparar la estrategia legal de suspensión, agenda una evaluación directa con nuestros abogados especialistas.\n\n"
                f"👉 *Haz clic aquí para agendar y pagar tu consulta:*\nhttps://mediacionesrjz.cl/profesionales"
            )
            
            return {
                "expulsion_type": "administrativa",
                "video_url": video_url,
                "default_message": msg
            }, False
        
        elif extracted.expulsion_type == "judicial" or context.get("expulsion_type") == "judicial":
            # RAMA B: Expulsión Judicial (Tribunal Penal)
            video_url = "https://mediacionesrjz.cl/expulsionrjz.mp4"
            
            msg = (
                "⚖️ *EXPULSIÓN JUDICIAL*\n\n"
                "*Tipo identificado:* Expulsión Judicial\n\n"
                "📋 *Causa habitual:* Sustitución de una pena privativa de libertad dictada por un Juzgado de Garantía o Tribunal Penal\n\n"
                "⚖️ *Naturaleza:* Es una pena sustitutiva dictada por un juez penal. Obliga a salir del país en lugar de cumplir la condena en prisión.\n\n"
                "📝 *Vía de impugnación:* Se apela mediante un recurso penal en un plazo habitual de *5 a 10 días* desde la sentencia.\n\n"
                "🚫 *Prohibición de retorno:* Impone una prohibición de reingreso por *10 años*. Si la persona regresa antes, deberá cumplir la pena en la cárcel.\n\n"
                "⚠️ *Cada día cuenta.* Analizamos tu causa penal y evaluamos las opciones legales disponibles antes de que la sentencia quede firme.\n\n"
                f"👉 *Haz clic aquí para agendar y pagar tu consulta:*\nhttps://mediacionesrjz.cl/profesionales"
            )
            
            return {
                "expulsion_type": "judicial",
                "video_url": video_url,
                "default_message": msg
            }, False
        
        # Si no sabemos el tipo de expulsión, iniciar flujo de preguntas
        if not context.get("expulsion_flow_started"):
            # 🧹 Limpiar cualquier estado residual de flujos previos
            context.pop("awaiting_document_confirmation", None)
            context.pop("awaiting_document_issuer", None)
            context.pop("awaiting_criminal_process", None)
            context.pop("expulsion_type", None)
            context.pop("has_document", None)
            context.pop("document_issuer", None)
            context.pop("in_criminal_process", None)
            
            # Primera pregunta: ¿Tiene copia del documento?
            context["expulsion_flow_started"] = True
            context["awaiting_document_confirmation"] = True
            conversation.context = context
            
            # 🔧 CRÍTICO: Marcar el campo context como modificado para que SQLAlchemy lo persista
            from sqlalchemy.orm import attributes
            attributes.flag_modified(conversation, "context")
            
            import logging
            logger = logging.getLogger(__name__)
            logger.info(
                f"✅ INICIANDO FLUJO LIMPIO - contexto a guardar: "
                f"context_keys={list(context.keys())}, "
                f"expulsion_flow_started={context.get('expulsion_flow_started')}, "
                f"awaiting_document_confirmation={context.get('awaiting_document_confirmation')}"
            )
            
            await db.commit()
            
            logger.info(
                f"✅ DESPUÉS del commit - conversation.context: "
                f"context_keys={list(conversation.context.keys()) if conversation.context else []}, "
                f"expulsion_flow_started={conversation.context.get('expulsion_flow_started') if conversation.context else None}, "
                f"awaiting_document_confirmation={conversation.context.get('awaiting_document_confirmation') if conversation.context else None}"
            )
            
            return {
                "default_message": (
                    "👉 Para orientarte correctamente sobre tu caso de expulsión, necesito hacerte algunas preguntas:\n\n"
                    "*¿Tienes copia del documento o resolución de expulsión?*\n\n"
                    "Responde 'Sí' o 'No'"
                )
            }, False
        
        # Procesar respuestas del flujo
        if context.get("awaiting_document_confirmation"):
            # Usuario responde si tiene documento
            # Mejorar detección de respuestas afirmativas y negativas
            response_lower = message_text.lower().strip()
            
            import logging
            logger = logging.getLogger(__name__)
            logger.info(
                f"🔍 Procesando respuesta en awaiting_document_confirmation: "
                f"message_text='{message_text}', response_lower='{response_lower}'"
            )
            
            # Detectar respuestas afirmativas (más variaciones)
            affirmative_keywords = ["si", "sí", "s", "yes", "tengo", "sí tengo", "si tengo", "claro", "afirmativo", "correcto", "efectivamente"]
            has_document = any(keyword in response_lower for keyword in affirmative_keywords)
            
            # Si no es afirmativo, verificar si es negativo explícito
            negative_keywords = ["no", "nop", "nope", "negativo", "no tengo", "no lo tengo"]
            is_negative = any(keyword in response_lower for keyword in negative_keywords)
            
            logger.info(
                f"🔍 Detección: has_document={has_document}, is_negative={is_negative}"
            )
            is_negative = any(keyword in response_lower for keyword in negative_keywords)
            
            # Si no detectamos claramente, volver a preguntar
            if not has_document and not is_negative:
                return {
                    "default_message": (
                        "No entendí bien tu respuesta. *¿Tienes copia del documento o resolución de expulsión?*\n\n"
                        "Por favor responde claramente 'Sí' o 'No'"
                    )
                }, False
            
            context["awaiting_document_confirmation"] = False
            context["has_document"] = has_document
            
            logger.info(
                f"✅ Actualizando contexto: awaiting_document_confirmation=False, has_document={has_document}"
            )
            
            if has_document:
                # Preguntar quién emitió el documento
                context["awaiting_document_issuer"] = True
                conversation.context = context
                
                # 🔧 CRÍTICO: Marcar el campo context como modificado
                from sqlalchemy.orm import attributes
                attributes.flag_modified(conversation, "context")
                
                await db.commit()
                
                logger.info(
                    f"✅ Contexto guardado: awaiting_document_issuer=True"
                )
                
                return {
                    "default_message": (
                        "👉 Perfecto. *¿Quién emite el documento?*\n\n"
                        "Responde:\n"
                        "1👉 SERMIG / PDI (organismo administrativo)\n"
                        "2👉 Tribunal (Juzgado de Garantía o Tribunal Penal)"
                    )
                }, False
            else:
                # No tiene documento, preguntar si está en proceso penal
                context["awaiting_criminal_process"] = True
                conversation.context = context
                
                # 🔧 CRÍTICO: Marcar el campo context como modificado
                from sqlalchemy.orm import attributes
                attributes.flag_modified(conversation, "context")
                
                await db.commit()
                
                logger.info(
                    f"✅ Contexto guardado: awaiting_criminal_process=True"
                )
                
                return {
                    "default_message": (
                        "👉 Entiendo. *¿La persona está en un proceso penal?*\n\n"
                        "Responde 'Sí' o 'No'"
                    )
                }, False
        
        if context.get("awaiting_document_issuer"):
            # Usuario responde quién emitió el documento
            issuer_text = message_text.lower()
            
            if "sermig" in issuer_text or "pdi" in issuer_text or "1" in issuer_text or "administrativo" in issuer_text:
                # RAMA A: Administrativa
                context["expulsion_type"] = "administrativa"
                context["awaiting_document_issuer"] = False
                
                # 🧹 LIMPIAR contexto - flujo completado
                context = clean_expulsion_flow_context(context, conversation)
                
                await db.commit()
                
                video_url = "https://mediacionesrjz.cl/expulsionrjz.mp4"
                
                msg = (
                    "⚖️ *EXPULSIÓN ADMINISTRATIVA*\n\n"
                    "*Tipo identificado:* Expulsión Administrativa\n\n"
                    "📋 *Causa habitual:* Ingreso por paso no habilitado, vencimiento de visa o infracción a la Ley de Migraciones\n\n"
                    "⏰ *Plazo de acción:* Dispones de *5 días hábiles* desde la notificación para interponer un Recurso de Reclamación ante la Corte de Apelaciones.\n\n"
                    "🛡️ *Efecto clave:* Presentar el recurso dentro del plazo suspende de inmediato la ejecución de la medida hasta que la justicia resuelva.\n\n"
                    "🚫 *Prohibición de retorno:* Se fija entre *2 y 10 años*, según la resolución.\n\n"
                    "⚠️ *El tiempo es crítico.* Para revisar tu notificación, calcular el plazo exacto y preparar la estrategia legal de suspensión, agenda una evaluación directa con nuestros abogados especialistas.\n\n"
                    f"👉 *Haz clic aquí para agendar y pagar tu consulta:*\nhttps://mediacionesrjz.cl/profesionales"
                )
                
                return {
                    "expulsion_type": "administrativa",
                    "video_url": video_url,
                    "default_message": msg
                }, False
            
            elif "tribunal" in issuer_text or "2" in issuer_text or "juzgado" in issuer_text or "penal" in issuer_text:
                # RAMA B: Judicial
                context["expulsion_type"] = "judicial"
                context["awaiting_document_issuer"] = False
                
                # 🧹 LIMPIAR contexto - flujo completado
                context = clean_expulsion_flow_context(context, conversation)
                
                await db.commit()
                
                video_url = "https://mediacionesrjz.cl/expulsionrjz.mp4"
                
                msg = (
                    "⚖️ *EXPULSIÓN JUDICIAL*\n\n"
                    "*Tipo identificado:* Expulsión Judicial\n\n"
                    "📋 *Causa habitual:* Sustitución de una pena privativa de libertad dictada por un Juzgado de Garantía o Tribunal Penal\n\n"
                    "⚖️ *Naturaleza:* Es una pena sustitutiva dictada por un juez penal. Obliga a salir del país en lugar de cumplir la condena en prisión.\n\n"
                    "📝 *Vía de impugnación:* Se apela mediante un recurso penal en un plazo habitual de *5 a 10 días* desde la sentencia.\n\n"
                    "🚫 *Prohibición de retorno:* Impone una prohibición de reingreso por *10 años*. Si la persona regresa antes, deberá cumplir la pena en la cárcel.\n\n"
                    "⚠️ *Cada día cuenta.* Analizamos tu causa penal y evaluamos las opciones legales disponibles antes de que la sentencia quede firme.\n\n"
                    f"👉 *Haz clic aquí para agendar y pagar tu consulta:*\nhttps://mediacionesrjz.cl/profesionales"
                )
                
                return {
                    "expulsion_type": "judicial",
                    "video_url": video_url,
                    "default_message": msg
                }, False
            else:
                # No entendió, preguntar de nuevo
                return {
                    "default_message": (
                        "No entendí bien tu respuesta. Por favor indica:\n\n"
                        "1👉 SERMIG / PDI (organismo administrativo)\n"
                        "2👉 Tribunal (Juzgado de Garantía o Tribunal Penal)"
                    )
                }, False
        
        if context.get("awaiting_criminal_process"):
            # Usuario responde si está en proceso penal
            # Mejorar detección de respuestas afirmativas y negativas
            response_lower = message_text.lower().strip()
            
            # Detectar respuestas afirmativas
            affirmative_keywords = ["si", "sí", "s", "yes", "estoy", "sí estoy", "si estoy", "claro", "afirmativo", "correcto"]
            in_criminal_process = any(keyword in response_lower for keyword in affirmative_keywords)
            
            # Si no es afirmativo, verificar si es negativo explícito
            negative_keywords = ["no", "nop", "nope", "negativo", "no estoy"]
            is_negative = any(keyword in response_lower for keyword in negative_keywords)
            
            # Si no detectamos claramente, volver a preguntar
            if not in_criminal_process and not is_negative:
                return {
                    "default_message": (
                        "No entendí bien tu respuesta. *¿La persona está en un proceso penal?*\n\n"
                        "Por favor responde claramente 'Sí' o 'No'"
                    )
                }, False
            
            context["awaiting_criminal_process"] = False
            conversation.context = context
            await db.commit()
            
            if in_criminal_process:
                # RAMA B: Judicial
                context["expulsion_type"] = "judicial"
                
                # 🧹 LIMPIAR contexto - flujo completado
                context = clean_expulsion_flow_context(context, conversation)
                
                await db.commit()
                
                video_url = "https://mediacionesrjz.cl/expulsionrjz.mp4"
                
                msg = (
                    "⚖️ *EXPULSIÓN JUDICIAL*\n\n"
                    "*Tipo identificado:* Expulsión Judicial\n\n"
                    "📋 *Causa habitual:* Sustitución de una pena privativa de libertad dictada por un Juzgado de Garantía o Tribunal Penal\n\n"
                    "⚖️ *Naturaleza:* Es una pena sustitutiva dictada por un juez penal. Obliga a salir del país en lugar de cumplir la condena en prisión.\n\n"
                    "📝 *Vía de impugnación:* Se apela mediante un recurso penal en un plazo habitual de *5 a 10 días* desde la sentencia.\n\n"
                    "🚫 *Prohibición de retorno:* Impone una prohibición de reingreso por *10 años*. Si la persona regresa antes, deberá cumplir la pena en la cárcel.\n\n"
                    "⚠️ *Cada día cuenta.* Analizamos tu causa penal y evaluamos las opciones legales disponibles antes de que la sentencia quede firme.\n\n"
                    f"👉 *Haz clic aquí para agendar y pagar tu consulta:*\nhttps://mediacionesrjz.cl/profesionales"
                )
                
                return {
                    "expulsion_type": "judicial",
                    "video_url": video_url,
                    "default_message": msg
                }, False
            else:
                # RAMA A: Administrativa
                context["expulsion_type"] = "administrativa"
                
                # 🧹 LIMPIAR contexto - flujo completado
                context = clean_expulsion_flow_context(context, conversation)
                
                await db.commit()
                
                video_url = "https://mediacionesrjz.cl/expulsionrjz.mp4"
                
                msg = (
                    "⚖️ *EXPULSIÓN ADMINISTRATIVA*\n\n"
                    "*Tipo identificado:* Expulsión Administrativa\n\n"
                    "📋 *Causa habitual:* Ingreso por paso no habilitado, vencimiento de visa o infracción a la Ley de Migraciones\n\n"
                    "⏰ *Plazo de acción:* Dispones de *5 días hábiles* desde la notificación para interponer un Recurso de Reclamación ante la Corte de Apelaciones.\n\n"
                    "🛡️ *Efecto clave:* Presentar el recurso dentro del plazo suspende de inmediato la ejecución de la medida hasta que la justicia resuelva.\n\n"
                    "🚫 *Prohibición de retorno:* Se fija entre *2 y 10 años*, según la resolución.\n\n"
                    "⚠️ *El tiempo es crítico.* Para revisar tu notificación, calcular el plazo exacto y preparar la estrategia legal de suspensión, agenda una evaluación directa con nuestros abogados especialistas.\n\n"
                    f"👉 *Haz clic aquí para agendar y pagar tu consulta:*\nhttps://mediacionesrjz.cl/profesionales"
                )
                
                return {
                    "expulsion_type": "administrativa",
                    "video_url": video_url,
                    "default_message": msg
                }, False
        
        # Fallback si no se cumplió ningún flujo
        return {
            "default_message": (
                "Para evitar la ejecución de una orden de expulsión es indispensable actuar dentro de los plazos legales.\n\n"
                "Agenda una revisión urgente de tu caso con nuestro equipo legal en el siguiente enlace:\n\n"
                "👉 *Agendar consulta con un abogado especialista:*\nhttps://mediacionesrjz.cl/profesionales"
            )
        }, False

    # ----------------------------------------------------------
    # UNKNOWN
    # ----------------------------------------------------------

    else:
        # Mensaje de fallback con logo, horario de atención y opciones claras
        logo_url = "https://mediacionesrjz.cl/logo.jpg"
        
        fallback_caption = (
            f"No entendí bien tu consulta 😊\n\n"
            f"Puedo ayudarte con:\n\n"
            f"📋 *Información sobre nuestros servicios legales*\n"
            f"⚖️ *Consultas sobre casos familiares o civiles*\n"
            f"💰 *Información de honorarios*\n"
            f"📅 *Agendar consultas*\n"
            f"📍 *Horarios y ubicación*\n"
            f"👨‍⚖️ *Hablar con un abogado*\n\n"
            f"🕒 *Horario de atención:* Lunes a Viernes de 9:00 a 18:00 hrs\n\n"
            f"¿En qué podemos asesorarte?"
        )
        
        return {
            "greeting_with_image": True,
            "image_url": logo_url,
            "caption": fallback_caption
        }, False


