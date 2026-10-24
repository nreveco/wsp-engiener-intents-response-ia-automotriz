import logging

import httpx

logger = logging.getLogger(__name__)

GRAPH_API_URL = "https://graph.facebook.com/v19.0/{phone_number_id}/messages"


async def send_text_message(
    whatsapp_token: str,
    phone_number_id: str,
    to_phone: str,
    message: str,
) -> bool:
    """Envía un mensaje de texto simple vía Meta Cloud API."""
    url = GRAPH_API_URL.format(phone_number_id=phone_number_id)

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone,
        "type": "text",
        "text": {"preview_url": False, "body": message},
    }

    headers = {
        "Authorization": f"Bearer {whatsapp_token}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                logger.info(f"Mensaje enviado a {to_phone}")
                return True
            else:
                logger.error(
                    f"Error enviando mensaje a {to_phone}: "
                    f"{response.status_code} {response.text}"
                )
                return False
    except Exception as exc:
        logger.error(f"Excepción al enviar mensaje WhatsApp: {exc}")
        return False


async def send_image_with_caption(
    whatsapp_token: str,
    phone_number_id: str,
    to_phone: str,
    image_url: str,
    caption: str,
) -> bool:
    """Envía una imagen con texto (caption) vía Meta Cloud API."""
    url = GRAPH_API_URL.format(phone_number_id=phone_number_id)

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone,
        "type": "image",
        "image": {
            "link": image_url,
            "caption": caption
        },
    }

    headers = {
        "Authorization": f"Bearer {whatsapp_token}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, json=payload, headers=headers)
            logger.info(f"WhatsApp API response for image: status={response.status_code}, body={response.text}")
            if response.status_code == 200:
                logger.info(f"Imagen enviada a {to_phone}")
                return True
            else:
                logger.error(
                    f"Error enviando imagen a {to_phone}: "
                    f"{response.status_code} {response.text}"
                )
                return False
    except Exception as exc:
        logger.error(f"Excepción al enviar imagen WhatsApp: {exc}")
        return False


async def send_video_with_caption(
    whatsapp_token: str,
    phone_number_id: str,
    to_phone: str,
    video_url: str,
    caption: str = None,
) -> bool:
    """
    Envía un video con texto opcional (caption) vía Meta Cloud API.
    
    IMPORTANTE: Meta WhatsApp acepta videos de dos formas:
    1. URL pública directa (link) - El video debe ser accesible públicamente
    2. Media ID (id) - Subir primero el video y luego usar el ID
    
    Esta función usa la opción 1 (link) que es más simple pero requiere
    que la URL sea accesible públicamente desde los servidores de Meta.
    """
    url = GRAPH_API_URL.format(phone_number_id=phone_number_id)

    video_payload = {
        "link": video_url
    }
    
    if caption:
        video_payload["caption"] = caption

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone,
        "type": "video",
        "video": video_payload,
    }

    headers = {
        "Authorization": f"Bearer {whatsapp_token}",
        "Content-Type": "application/json",
    }

    logger.info(
        f"Intentando enviar video a {to_phone}",
        extra={
            "video_url": video_url,
            "has_caption": bool(caption),
            "to_phone": to_phone
        }
    )

    try:
        async with httpx.AsyncClient(timeout=30) as client:  # Aumentado timeout para videos
            response = await client.post(url, json=payload, headers=headers)
            logger.info(
                f"WhatsApp API response for video: status={response.status_code}, body={response.text}",
                extra={
                    "status_code": response.status_code,
                    "response_body": response.text,
                    "video_url": video_url
                }
            )
            if response.status_code == 200:
                logger.info(f"✅ Video enviado exitosamente a {to_phone}")
                return True
            else:
                logger.error(
                    f"❌ Error enviando video a {to_phone}: {response.status_code} {response.text}",
                    extra={
                        "status_code": response.status_code,
                        "error_response": response.text,
                        "video_url": video_url
                    }
                )
                return False
    except Exception as exc:
        logger.error(
            f"❌ Excepción al enviar video WhatsApp: {exc}",
            exc_info=exc,
            extra={"video_url": video_url, "to_phone": to_phone}
        )
        return False


async def mark_as_read(
    whatsapp_token: str,
    phone_number_id: str,
    wa_message_id: str,
) -> None:
    """Marca el mensaje entrante como leído (doble palomita azul)."""
    url = GRAPH_API_URL.format(phone_number_id=phone_number_id)

    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": wa_message_id,
    }

    headers = {
        "Authorization": f"Bearer {whatsapp_token}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(url, json=payload, headers=headers)
    except Exception:
        pass  # No crítico si falla
