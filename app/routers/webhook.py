import logging
import uuid
import time
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.ai.intent_classifier import classify_intent
from app.intents.definitions import ExtractedIntent
from app.ai.response_builder import build_response
from app.config import settings
from app.db.database import get_db
from app.db.models import (
    Business,
    BusinessSettings,
    LegalCategory,
    Conversation,
    ConversationStatus,
    Message,
    BusinessType,
)
from app.intents.definitions import Intent
from app.routers.webhook_legal_route import _route_intent_legal
from app.routers.webhook_automotive_route import route_intent_automotive
from app.services import handoff, leads, notifications
from app.ai.media_processor import analyze_image, extract_pdf_text, transcribe_audio
from app.whatsapp.gateway import mark_as_read, send_text_message
from app.whatsapp.media import download_media

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])

# Cache en memoria con timestamps para detectar mensajes siendo procesados
# Previene que webhooks duplicados procesen el mismo mensaje simultaneamente
# Formato: {wa_message_id: timestamp}
_processing_messages: Dict[str, float] = {}
_CACHE_TIMEOUT_SECONDS = 120  # Limpiar entradas despues de 2 minutos


def _cleanup_expired_cache():
    """Limpia mensajes del cache que llevan mas de CACHE_TIMEOUT_SECONDS"""
    current_time = time.time()
    expired_keys = [
        msg_id for msg_id, timestamp in _processing_messages.items()
        if current_time - timestamp > _CACHE_TIMEOUT_SECONDS
    ]
    for msg_id in expired_keys:
        _processing_messages.pop(msg_id, None)
    if expired_keys:
        logger.info(f"Limpiados {len(expired_keys)} mensajes expirados del cache")


# ──────────────────────────────────────────────────────────────
# GET — verificación del webhook Meta
# ──────────────────────────────────────────────────────────────

@router.get("/{phone_number_id}")
async def verify_webhook(
    phone_number_id: str,
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    """
    Meta llama a esta URL para verificar el webhook.
    Retorna el challenge si el token coincide.
    """
    if hub_mode == "subscribe" and hub_challenge:
        if hub_verify_token == settings.whatsapp_verify_token:
            logger.info(f"Webhook verificado para phone_number_id={phone_number_id}")
            return int(hub_challenge)
        raise HTTPException(status_code=403, detail="Invalid verify token")

    raise HTTPException(status_code=400, detail="Missing hub parameters")


# ──────────────────────────────────────────────────────────────
# POST — recibe mensajes entrantes de WhatsApp
# ──────────────────────────────────────────────────────────────

@router.post("/{phone_number_id}")
async def receive_message(
    phone_number_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Pipeline principal:
    1. Parsear payload Meta
    2. Buscar negocio en DB
    3. Clasificar intención (IA)
    4. Ejecutar acción (backend real)
    5. Construir respuesta (IA)
    6. Enviar por WhatsApp
    """
    media_label = ""  # prefijo para el inbound Message guardado en DB

    # ── Buscar negocio ──────────────────────────────────────────
    logger.info(
        "Lookup business for incoming webhook",
        extra={
            "phone_number_id": phone_number_id,
            "env_whatsapp_phone_number_id": settings.whatsapp_phone_number_id,
        },
    )

    stmt = select(Business).where(
        Business.phone_number_id == phone_number_id,
        Business.is_active == True,
    )
    result = await db.execute(stmt)
    business = result.scalar_one_or_none()

    if not business and settings.whatsapp_phone_number_id:
        logger.info(
            "Incoming phone_number_id not registered, falling back to env WHATSAPP_PHONE_NUMBER_ID",
            extra={
                "incoming_phone_number_id": phone_number_id,
                "fallback_phone_number_id": settings.whatsapp_phone_number_id,
            },
        )
        stmt = select(Business).where(
            Business.phone_number_id == settings.whatsapp_phone_number_id,
            Business.is_active == True,
        )
        result = await db.execute(stmt)
        business = result.scalar_one_or_none()

    if not business:
        active_stmt = select(Business.phone_number_id).where(Business.is_active == True)
        active_result = await db.execute(active_stmt)
        active_ids = [row[0] for row in active_result.all()]
        logger.warning(
            f"phone_number_id no registrado: {phone_number_id}. "
            f"Active phone_number_ids={active_ids}"
        )
        return {"status": "business_not_found"}

    logger.info(
        "Business found for webhook request",
        extra={
            "phone_number_id": phone_number_id,
            "business_id": business.id,
            "business_name": business.name,
        },
    )

    whatsapp_token = settings.whatsapp_token
    whatsapp_phone_number_id = settings.whatsapp_phone_number_id
    if not whatsapp_token or not whatsapp_phone_number_id:
        logger.error(
            "Faltan credenciales de WhatsApp en el archivo .env",
            extra={
                "whatsapp_token": bool(whatsapp_token),
                "whatsapp_phone_number_id": bool(whatsapp_phone_number_id),
            },
        )
        return {
            "status": "missing_whatsapp_env_credentials",
            "error": "Missing WHATSAPP_TOKEN or WHATSAPP_PHONE_NUMBER_ID",
        }

    # ── Parsear payload WhatsApp ────────────────────────────────
    try:
        body = await request.json()
    except Exception as exc:
        raw_body = (await request.body()).decode("utf-8", "replace")
        logger.error(
            "Error leyendo payload JSON del webhook",
            extra={
                "error": str(exc),
                "content_type": request.headers.get("content-type"),
                "body_snippet": raw_body[:200],
            },
        )
        return {
            "status": "invalid_json_payload",
            "error": str(exc),
        }

    try:
        logger.info("Parsing WhatsApp payload", extra={"body_keys": list(body.keys())})
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages_list = value.get("messages", [])

        if not messages_list:
            logger.warning(
                "Webhook payload contains no WhatsApp messages",
                extra={"payload_value": value},
            )
            return {"status": "no_messages"}

        wa_message = messages_list[0]

        wa_message_type = wa_message.get("type")
        customer_phone: str = wa_message["from"]
        wa_message_id: str = wa_message["id"]

        # ── Verificar si el mensaje ya está siendo procesado (previene webhooks duplicados simultaneos) ──
        # Primero limpiar entradas expiradas del cache
        _cleanup_expired_cache()
        
        if wa_message_id in _processing_messages:
            logger.info(
                f"Mensaje ya esta siendo procesado: {wa_message_id} - ignorando webhook duplicado",
                extra={"wa_message_id": wa_message_id, "customer_phone": customer_phone}
            )
            return {"status": "already_processing", "wa_message_id": wa_message_id}
        
        # Marcar como "en procesamiento" con timestamp
        _processing_messages[wa_message_id] = time.time()

        contacts = value.get("contacts", [])
        customer_name = contacts[0].get("profile", {}).get("name", "") if contacts else ""

        logger.info(
            "Parsed incoming WhatsApp message",
            extra={
                "phone_number_id": phone_number_id,
                "message_type": wa_message_type,
                "customer_phone": customer_phone,
                "customer_name": customer_name,
                "wa_message_id": wa_message_id,
            },
        )

        if wa_message_type == "text":
            message_text = wa_message["text"]["body"].strip()

        elif wa_message_type == "interactive":
            inter = wa_message.get("interactive", {})
            if inter.get("type") == "button_reply":
                message_text = inter["button_reply"].get("title", "")
            elif inter.get("type") == "list_reply":
                message_text = inter["list_reply"].get("title", "")
            else:
                _processing_messages.pop(wa_message_id, None)  # Limpiar cache antes de salir
                return {"status": "unsupported_interactive_type"}

        elif wa_message_type == "audio":
            audio_id = wa_message["audio"]["id"]
            try:
                audio_bytes, audio_mime = await download_media(whatsapp_token, audio_id)
                transcribed = await transcribe_audio(audio_bytes, audio_mime)
            except Exception as exc:
                logger.warning(f"Error procesando audio {audio_id}: {exc}")
                transcribed = ""
            if not transcribed:
                await mark_as_read(whatsapp_token, whatsapp_phone_number_id, wa_message_id)
                await send_text_message(
                    whatsapp_token, whatsapp_phone_number_id, customer_phone,
                    "🎙️ No pude entender tu mensaje de voz. ¿Puedes escribir tu consulta? 😊"
                )
                _processing_messages.pop(wa_message_id, None)  # Limpiar cache antes de salir
                return {"status": "audio_transcription_failed"}
            message_text = transcribed
            media_label = "🎙️ "

        elif wa_message_type == "image":
            img = wa_message["image"]
            caption = img.get("caption", "").strip()
            try:
                img_bytes, img_mime = await download_media(whatsapp_token, img["id"])
                img_desc = await analyze_image(img_bytes, img_mime, business.name)
            except Exception as exc:
                logger.warning(f"Error procesando imagen: {exc}")
                img_desc = ""
            if not img_desc and not caption:
                await send_text_message(
                    whatsapp_token, whatsapp_phone_number_id, customer_phone,
                    "🖼️ Recibí tu imagen pero no pude interpretarla. ¿Puedes describirme qué necesitas?"
                )
                _processing_messages.pop(wa_message_id, None)  # Limpiar cache antes de salir
                return {"status": "image_analysis_failed"}
            message_text = f"{caption} {img_desc}".strip() if caption else img_desc or caption
            media_label = "🖼️ "

        elif wa_message_type == "document":
            doc = wa_message.get("document", {})
            doc_mime = doc.get("mime_type", "").lower()
            doc_filename = doc.get("filename", "").lower()
            if "pdf" not in doc_mime and not doc_filename.endswith(".pdf"):
                _processing_messages.pop(wa_message_id, None)  # Limpiar cache antes de salir
                return {"status": "unsupported_document_type"}
            try:
                pdf_bytes, _ = await download_media(whatsapp_token, doc["id"])
                pdf_text = await extract_pdf_text(pdf_bytes)
            except Exception as exc:
                logger.warning(f"Error procesando PDF: {exc}")
                pdf_text = ""
            if not pdf_text.strip():
                await send_text_message(
                    whatsapp_token, whatsapp_phone_number_id, customer_phone,
                    "📄 Recibí tu PDF pero no pude extraer el texto. ¿Puedes describirme qué necesitas?"
                )
                _processing_messages.pop(wa_message_id, None)  # Limpiar cache antes de salir
                return {"status": "pdf_empty"}
            message_text = pdf_text
            media_label = "📄 "

        else:
            _processing_messages.pop(wa_message_id, None)  # Limpiar cache antes de salir
            return {"status": "unsupported_message_type"}

    except (KeyError, IndexError, TypeError) as exc:
        logger.error(f"Error parseando payload WhatsApp: {exc} | body={body}")
        _processing_messages.pop(wa_message_id, None)  # Limpiar cache antes de salir
        return {"status": "parse_error"}

    # ── Verificar si el mensaje ya fue procesado (deduplicación) ──
    # IMPORTANTE: Verificar ANTES de cualquier otra operación para prevenir duplicados
    stmt_check = select(Message.id).where(Message.wa_message_id == wa_message_id).limit(1)
    result_check = await db.execute(stmt_check)
    existing_id = result_check.scalar_one_or_none()
    
    if existing_id:
        logger.info(
            f"Mensaje duplicado detectado: {wa_message_id} - ignorando",
            extra={
                "wa_message_id": wa_message_id,
                "customer_phone": customer_phone,
                "existing_message_id": existing_id,
            }
        )
        _processing_messages.pop(wa_message_id, None)  # Limpiar cache antes de salir
        return {"status": "duplicate_message", "wa_message_id": wa_message_id}

    # ── Marcar como leído (no bloqueante) ───────────────────────
    await mark_as_read(whatsapp_token, whatsapp_phone_number_id, wa_message_id)

    # ── Obtener/crear conversación ──────────────────────────────
    # Buscar conversación activa existente
    conv_stmt = (
        select(Conversation)
        .where(
            Conversation.business_id == business.id,
            Conversation.customer_phone == customer_phone,
            Conversation.status == ConversationStatus.ACTIVE,
        )
        .order_by(Conversation.created_at.desc())
        .limit(1)
    )
    conv_result = await db.execute(conv_stmt)
    conversation = conv_result.scalar_one_or_none()

    is_new_conversation = False
    if not conversation:
        conversation = Conversation(
            id=str(uuid.uuid4()),
            business_id=business.id,
            customer_phone=customer_phone,
            customer_name=customer_name,
            status=ConversationStatus.ACTIVE,
            context={"history": [], "cart": []},
        )
        db.add(conversation)
        await db.flush()
        is_new_conversation = True
        logger.info(
            f"Nueva conversación: {conversation.id} con {customer_phone}",
            extra={
                "conversation_id": conversation.id,
                "customer_phone": customer_phone,
                "business_id": business.id,
            }
        )
    else:
        logger.info(
            f"Usando conversación existente: {conversation.id}",
            extra={
                "conversation_id": conversation.id,
                "customer_phone": customer_phone,
                "business_id": business.id,
            }
        )
        if customer_name and not conversation.customer_name:
            conversation.customer_name = customer_name

    # ── Si está en handoff, no tocar ────────────────────────────
    if conversation.status == ConversationStatus.HUMAN_HANDOFF:
        logger.info(f"Conversación {conversation.id} en handoff — ignorando mensaje")
        _processing_messages.pop(wa_message_id, None)  # Limpiar cache antes de salir
        return {"status": "human_handoff_active"}

    # ── Contexto del negocio para la IA ──────────────────────────
    cat_stmt = select(LegalCategory.name).where(
        LegalCategory.business_id == business.id,
        LegalCategory.is_active == True,
    )
    cat_result = await db.execute(cat_stmt)
    category_names = [row[0] for row in cat_result.all()]

    logger.info(
        "Step 1: Media processed, handing off to intent classifier",
        extra={
            "phone_number_id": phone_number_id,
            "business_id": business.id,
            "message_text": message_text,
            "media_label": media_label,
        },
    )

    # 🔄 CRÍTICO: Refrescar conversation desde BD ANTES de verificar contexto
    # Esto asegura que tenemos el contexto más actualizado si fue modificado en un request anterior
    # Usar no_autoflush para evitar flush prematuro de mensajes pendientes
    with db.no_autoflush:
        await db.refresh(conversation)
    
    # 🔧 IMPORTANTE: Leer history DESPUÉS del refresh para tener el contexto actualizado
    history: list = (conversation.context or {}).get("history", [])

    # ⚠️ IMPORTANTE: Verificar si está en flujo de expulsión ANTES de clasificar
    context = conversation.context or {}
    
    logger.info(
        f"📋 Contexto leído: keys={list(context.keys())}, "
        f"expulsion_flow_started={context.get('expulsion_flow_started')}, "
        f"awaiting_document_confirmation={context.get('awaiting_document_confirmation')}"
    )
    
    in_expulsion_flow = (
        context.get("expulsion_flow_started") and 
        (context.get("awaiting_document_confirmation") or 
         context.get("awaiting_document_issuer") or 
         context.get("awaiting_criminal_process"))
    )
    
    # ── PASO 1: Clasificar intención ────────────────────────────
    
    # Primero clasificar la intención (sin forzar todavía)
    extracted = await classify_intent(
        message=message_text,
        business_name=business.name,
        business_type=business.business_type.value if business.business_type else "general",
        categories=category_names,
        conversation_history=history,
    )
    intent = extracted.intent
    
    # 🔄 DETECCIÓN INTELIGENTE: Distinguir entre respuesta al flujo vs cambio de tema
    reset_intents = [Intent.GREETING, Intent.THANKS, Intent.HUMAN_SUPPORT]
    is_awaiting_response = (
        context.get("awaiting_document_confirmation") or 
        context.get("awaiting_document_issuer") or 
        context.get("awaiting_criminal_process")
    )
    
    # Detectar si es una respuesta corta típica del flujo (sí/no/sermig/pdi/tribunal)
    message_lower = message_text.lower().strip()
    flow_response_keywords = ["si", "sí", "no", "nop", "sermig", "pdi", "tribunal", "juzgado", "garantia", "garantía", "penal"]
    is_likely_flow_response = (
        is_awaiting_response and 
        len(message_lower.split()) <= 3 and  # Máximo 3 palabras
        any(keyword in message_lower for keyword in flow_response_keywords)
    )
    
    # 🚨 FALLBACK: Si el clasificador falló (UNKNOWN) y el mensaje es claramente un reset
    reset_keywords = ["hola", "gracias", "ayuda", "humano", "persona", "asesor", "abogado"]
    is_explicit_reset_message = (
        intent == Intent.UNKNOWN and 
        in_expulsion_flow and
        any(keyword in message_lower for keyword in reset_keywords) and
        not is_likely_flow_response
    )
    
    if is_explicit_reset_message:
        logger.info(
            f"🚨 FALLBACK RESET: Clasificador devolvió UNKNOWN pero mensaje '{message_text}' "
            f"contiene keyword de reset - tratando como cambio de tema"
        )
        # Forzar intención de reset para que se ejecute la lógica de limpieza
        intent = Intent.GREETING
    
    logger.info(
        f"🧠 Análisis de intención: intent={intent.value}, "
        f"is_awaiting_response={is_awaiting_response}, "
        f"is_likely_flow_response={is_likely_flow_response}, "
        f"message='{message_text}'"
    )
    
    # CASO 1: Usuario dice intención de reset EXPLÍCITA (no es respuesta corta al flujo)
    if intent in reset_intents and in_expulsion_flow and not is_likely_flow_response:
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
            f"✅ Contexto limpiado - procesando intención {intent.value}"
        )
    
    # CASO 2: Parece una respuesta al flujo (corta y con keywords) - ignorar la intención y procesar como flujo
    elif is_likely_flow_response:
        logger.info(
            f"✅ Respuesta detectada como parte del flujo - ignorando intent={intent.value}, "
            f"forzando EXPULSION_INQUIRY"
        )
    
    # Si SIGUE en flujo de expulsión (no fue reseteado), forzar EXPULSION_INQUIRY
    if in_expulsion_flow:
        logger.info(
            "🔄 Usuario en flujo de expulsión - forzando intención EXPULSION_INQUIRY",
            extra={
                "awaiting_document_confirmation": context.get("awaiting_document_confirmation"),
                "awaiting_document_issuer": context.get("awaiting_document_issuer"),
                "awaiting_criminal_process": context.get("awaiting_criminal_process"),
            }
        )
        # Crear un objeto extracted mínimo para que el router funcione
        extracted = ExtractedIntent(
            intent=Intent.EXPULSION_INQUIRY,
            expulsion_type=context.get("expulsion_type"),
            has_document=context.get("has_document"),
            document_issuer=context.get("document_issuer"),
            in_criminal_process=context.get("in_criminal_process"),
        )
        intent = Intent.EXPULSION_INQUIRY
    
    logger.info(
        "Intent classification completed",
        extra={
            "intent": intent.value,
            "extracted_product": getattr(extracted, 'product_name', None),
            "extracted_entities": extracted.dict(exclude={'intent'}),
            "forced_expulsion_flow": in_expulsion_flow,
        },
    )

    # ── Registrar lead (solo primera vez) ───────────────────────
    if is_new_conversation:
        await leads.register_lead(
            db, business.id, customer_phone, name=customer_name, intent=intent.value
        )
        if business.human_support_phone:
            await notifications.notify_new_lead(
                whatsapp_token=whatsapp_token,
                phone_number_id=whatsapp_phone_number_id,
                owner_phone=business.human_support_phone,
                customer_phone=customer_phone,
                customer_name=customer_name,
                first_intent=intent.value,
            )

    # ── PASO 2: Router de acciones ──────────────────────────────
    settings_stmt = select(BusinessSettings).where(BusinessSettings.business_id == business.id)
    settings_result = await db.execute(settings_stmt)
    biz_settings = settings_result.scalar_one_or_none()
    currency_symbol = biz_settings.currency_symbol if biz_settings else "$"

    if business.business_type == BusinessType.AUTOMOTIVE:
        query_result, interactive_sent = await route_intent_automotive(
            intent=intent,
            extracted=extracted,
            business=business,
            biz_settings=biz_settings,
            db=db,
            customer_phone=customer_phone,
            customer_name=customer_name,
            conversation=conversation,
            message_text=message_text,
        )
    else:
        query_result, interactive_sent = await _route_intent_legal(
            intent=intent,
            extracted=extracted,
            business=business,
            biz_settings=biz_settings,
            db=db,
            customer_phone=customer_phone,
            customer_name=customer_name,
            conversation=conversation,
            currency_symbol=currency_symbol,
            phone_number_id=phone_number_id,
            message_text=message_text,
        )
    
    # 🔄 CRÍTICO: Refrescar conversation desde BD para obtener contexto actualizado
    # El router puede haber modificado el contexto (ej: flujo de expulsión)
    await db.refresh(conversation)
    
    logger.info(
        "Step 2: Action router completed",
        extra={
            "intent": intent.value,
            "query_result": query_result,
            "interactive_sent": interactive_sent,
            "context_after_router": conversation.context,
        },
    )

    # ── PASO 3: Construir y enviar respuesta ────────────────────
    if not interactive_sent:
        # Si es greeting con imagen, usar el caption directamente
        if query_result.get("greeting_with_image"):
            logger.info(
                "Step 4: Using greeting with image - skipping response builder",
                extra={"query_result": query_result},
            )
            response_text = query_result["caption"]
        elif query_result.get("default_message") and not query_result.get("data"):
            logger.info(
                "Step 4: Using default message from action router",
                extra={"query_result": query_result},
            )
            response_text = query_result["default_message"]
        else:
            logger.info(
                "Step 4: Building response from query result",
                extra={"query_result": query_result},
            )
            response_text = await build_response(
                intent=intent.value,
                original_message=message_text,
                query_result=query_result,
                business_name=business.name,
                currency_symbol=currency_symbol,
            )
            logger.info(
                "Response builder completed",
                extra={"response_text": response_text},
            )

        # Guardar mensaje entrante
        inbound_msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            direction="inbound",
            content=f"{media_label}{message_text}" if media_label else message_text,
            intent=intent.value,
            wa_message_id=wa_message_id,
        )
        db.add(inbound_msg)

        # Guardar mensaje saliente ANTES de enviar por WhatsApp
        # Si es greeting con imagen, guardar el caption
        outbound_content = query_result.get("caption") if query_result.get("greeting_with_image") else response_text
        outbound_msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            direction="outbound",
            content=outbound_content,
            intent=intent.value,
        )
        db.add(outbound_msg)

        # Actualizar historial PRESERVANDO otras keys del contexto
        history.append({"role": "user", "content": message_text})
        history.append({"role": "assistant", "content": outbound_content})
        # 🔧 CRÍTICO: Preservar keys existentes (como expulsion_flow_started, awaiting_*)
        
        # 🔄 CRÍTICO: Refrescar conversation ANTES de actualizar contexto
        # El router puede haber modificado el contexto (ej: flujo de expulsión)
        # Usar no_autoflush para evitar flush prematuro de mensajes pendientes
        with db.no_autoflush:
            await db.refresh(conversation)
        
        logger.info(
            "💾 Antes de actualizar contexto",
            extra={
                "context_before": conversation.context,
                "conversation_id": conversation.id,
            }
        )
        
        ctx = dict(conversation.context or {})  # Copiar el contexto existente
        ctx["history"] = history[-8:]  # Actualizar solo el historial
        conversation.context = ctx
        
        # 🔧 CRÍTICO: Marcar el campo context como modificado para que SQLAlchemy lo persista
        from sqlalchemy.orm import attributes
        attributes.flag_modified(conversation, "context")
        
        logger.info(
            "💾 Después de actualizar contexto",
            extra={
                "context_after": conversation.context,
                "context_keys": list(conversation.context.keys()) if conversation.context else [],
                "conversation_id": conversation.id,
            }
        )
        
        # Commit a la base de datos - capturar IntegrityError por duplicados
        try:
            await db.commit()
        except IntegrityError as e:
            await db.rollback()
            if "wa_message_id" in str(e) and "unique" in str(e).lower():
                logger.warning(
                    f"Mensaje duplicado detectado durante commit: {wa_message_id} - webhook duplicado recibido mientras procesaba",
                    extra={
                        "wa_message_id": wa_message_id,
                        "customer_phone": customer_phone,
                        "error": str(e),
                    }
                )
                _processing_messages.pop(wa_message_id, None)  # Limpiar cache antes de salir
                return {"status": "duplicate_message_commit", "wa_message_id": wa_message_id}
            # Si es otro tipo de IntegrityError, re-lanzar
            raise

        # Enviar por WhatsApp (después del commit)
        # Verificar si es un mensaje de bienvenida con imagen
        if query_result.get("greeting_with_image"):
            from app.whatsapp.gateway import send_image_with_caption
            await send_image_with_caption(
                whatsapp_token=whatsapp_token,
                phone_number_id=whatsapp_phone_number_id,
                to_phone=customer_phone,
                image_url=query_result["image_url"],
                caption=query_result["caption"],
            )
        # Verificar si hay un video para enviar (expulsión)
        elif query_result.get("video_url"):
            from app.whatsapp.gateway import send_video_with_caption
            
            logger.info(
                "🎥 Detectado video_url en query_result - enviando video",
                extra={
                    "video_url": query_result.get("video_url"),
                    "customer_phone": customer_phone,
                    "intent": intent.value
                }
            )
            
            # Primero enviar el mensaje de texto (sin la URL del video en el texto)
            # Ya que el video se enviará como archivo multimedia separado
            text_without_video_url = response_text.split("🎥 *Video explicativo")[0].strip()
            await send_text_message(
                whatsapp_token=whatsapp_token,
                phone_number_id=whatsapp_phone_number_id,
                to_phone=customer_phone,
                message=text_without_video_url,
            )
            
            # Luego enviar el video como mensaje multimedia separado
            video_sent = await send_video_with_caption(
                whatsapp_token=whatsapp_token,
                phone_number_id=whatsapp_phone_number_id,
                to_phone=customer_phone,
                video_url=query_result["video_url"],
                caption="🎥 Video explicativo sobre expulsión - Mediaciones RJZ",
            )
            
            if video_sent:
                logger.info(
                    "✅ Video de expulsión enviado exitosamente",
                    extra={"customer_phone": customer_phone, "video_url": query_result.get("video_url")}
                )
            else:
                logger.error(
                    "❌ Falló el envío del video de expulsión",
                    extra={"customer_phone": customer_phone, "video_url": query_result.get("video_url")}
                )
        else:
            await send_text_message(
                whatsapp_token=whatsapp_token,
                phone_number_id=whatsapp_phone_number_id,
                to_phone=customer_phone,
                message=response_text,
            )
        logger.info(
            "Response sent successfully",
            extra={
                "customer_phone": customer_phone,
                "intent": intent.value,
                "conversation_id": conversation.id,
            }
        )
    else:
        # Guardar mensaje entrante cuando se envía mensaje interactivo
        inbound_msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation.id,
            direction="inbound",
            content=f"{media_label}{message_text}" if media_label else message_text,
            intent=intent.value,
            wa_message_id=wa_message_id,
        )
        db.add(inbound_msg)
        
        history.append({"role": "user", "content": message_text})
        history.append({"role": "assistant", "content": "[interactive]"})
        # 🔧 CRÍTICO: Preservar keys existentes (como expulsion_flow_started, awaiting_*)
        ctx = dict(conversation.context or {})  # Copiar el contexto existente
        ctx["history"] = history[-8:]  # Actualizar solo el historial
        conversation.context = ctx
        
        # 🔧 CRÍTICO: Marcar el campo context como modificado para que SQLAlchemy lo persista
        from sqlalchemy.orm import attributes
        attributes.flag_modified(conversation, "context")
        
        # Commit a la base de datos - capturar IntegrityError por duplicados
        try:
            await db.commit()
        except IntegrityError as e:
            await db.rollback()
            if "wa_message_id" in str(e) and "unique" in str(e).lower():
                logger.warning(
                    f"Mensaje duplicado detectado durante commit (interactive): {wa_message_id} - webhook duplicado recibido mientras procesaba",
                    extra={
                        "wa_message_id": wa_message_id,
                        "customer_phone": customer_phone,
                        "error": str(e),
                    }
                )
                _processing_messages.pop(wa_message_id, None)  # Limpiar cache antes de salir
                return {"status": "duplicate_message_commit", "wa_message_id": wa_message_id}
            # Si es otro tipo de IntegrityError, re-lanzar
            raise

    logger.info(f"[{business.name}] {customer_phone} → {intent.value}")
    
    # Remover del cache de procesamiento al finalizar exitosamente
    _processing_messages.pop(wa_message_id, None)
    
    return {"status": "ok", "intent": intent.value}
