"""Acciones iniciales del dominio automotriz."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.db.models import AutomotiveSettings, Business, BusinessSettings, Conversation
from app.intents.definitions import ExtractedIntent, Intent
from app.services.financing import calculate_financing
from app.services.vehicle_catalog import get_vehicle, search_vehicles


def _money(value: int | float, symbol: str) -> str:
    return f"{symbol}{int(value):,}".replace(",", ".")


async def route_intent_automotive(
    intent: Intent,
    extracted: ExtractedIntent,
    business: Business,
    biz_settings: BusinessSettings | None,
    db: AsyncSession,
    conversation: Conversation,
    customer_phone: str,
    customer_name: str,
    message_text: str,
) -> tuple[dict, bool]:
    """Ejecuta acciones determinísticas para intenciones automotrices."""
    currency_symbol = biz_settings.currency_symbol if biz_settings else "$"
    automotive_result = await db.execute(
        select(AutomotiveSettings).where(
            AutomotiveSettings.business_id == business.id
        )
    )
    automotive_settings = automotive_result.scalar_one_or_none()
    context = conversation.context or {}

    if intent == Intent.GREETING:
        return {
            "default_message": (
                f"¡Hola! 👋 Te damos la bienvenida a *{business.name}*.\n\n"
                "Soy el asistente encargado de apoyarte en la evaluación de tu próximo vehículo. "
                "Puedo ayudarte a buscar modelos, revisar precios y disponibilidad, "
                "simular financiamiento, coordinar una prueba de manejo o solicitar una tasación.\n\n"
                "¿Qué vehículo estás buscando?"
            )
        }, False

    if intent == Intent.THANKS:
        return {
            "default_message": (
                f"¡Gracias por contactar a *{business.name}*! 🚗\n\n"
                "Quedamos atentos para ayudarte con la evaluación de tu próximo vehículo, "
                "una simulación de financiamiento o cualquier otra consulta. "
                "¡Que tengas un excelente día!"
            )
        }, False

    if intent == Intent.HUMAN_SUPPORT:
        return {
            "default_message": (
                "Claro, te comunicaré con un asesor comercial. "
                f"También puedes escribirnos al {business.human_support_phone or 'nuestro canal de atención'}."
            )
        }, False

    if intent == Intent.HOURS_QUERY:
        return {
            "data": {"horarios": biz_settings.hours if biz_settings and biz_settings.hours else {}}
        }, False

    if intent == Intent.LOCATION_QUERY:
        return {
            "data": {
                "address": biz_settings.address if biz_settings else None,
                "city": biz_settings.city if biz_settings else None,
                "maps_url": biz_settings.maps_url if biz_settings else None,
            }
        }, False

    if intent in {
        Intent.VEHICLE_SEARCH,
        Intent.VEHICLE_AVAILABILITY,
        Intent.VEHICLE_PRICE,
    }:
        vehicles = await search_vehicles(
            db,
            business.id,
            brand=extracted.brand,
            model=extracted.model,
            body_type=extracted.body_type,
            transmission=extracted.transmission,
            year=extracted.year,
            color=extracted.color,
            max_budget=extracted.max_budget,
        )
        if not vehicles:
            return {
                "default_message": (
                    "No encontré vehículos que coincidan con esos criterios en el catálogo actual. "
                    "Si quieres, dime otra marca, modelo, presupuesto o característica."
                )
            }, False
        if len(vehicles) == 1:
            context["selected_vehicle"] = vehicles[0]
            conversation.context = context
            flag_modified(conversation, "context")
            await db.commit()
        return {"data": {"vehicles": vehicles}}, False

    if intent == Intent.VEHICLE_DETAILS:
        vehicle = await get_vehicle(
            db,
            business.id,
            brand=extracted.brand,
            model=extracted.model,
            year=extracted.year,
        )
        if not vehicle:
            return {"default_message": "No encontré ese vehículo en nuestro catálogo actual. ¿Puedes indicarme marca y modelo?"}, False
        return {"data": {"vehicle": vehicle}}, False

    if intent == Intent.FINANCING_QUOTE:
        previous = context.get("financing", {})
        selected_vehicle = context.get("selected_vehicle", {})
        price = (
            extracted.vehicle_price
            or previous.get("vehicle_price")
            or selected_vehicle.get("price")
        )
        down_payment = extracted.down_payment
        if down_payment is None:
            down_payment = previous.get("down_payment")
        installments = extracted.installments or previous.get("installments")
        rate = automotive_settings.monthly_interest_rate if automotive_settings else None

        financing_context = dict(previous)
        for field, value in (
            ("vehicle_price", price),
            ("down_payment", down_payment),
            ("installments", installments),
        ):
            if value is not None:
                financing_context[field] = value
        context["financing"] = financing_context
        conversation.context = context
        flag_modified(conversation, "context")
        await db.commit()

        missing = []
        if price is None:
            missing.append("el precio del vehículo")
        if down_payment is None:
            missing.append("el pie")
        if installments is None:
            missing.append("la cantidad de cuotas")
        if rate is None:
            return {
                "default_message": (
                    "Puedo preparar una simulación referencial, pero la tasa financiera "
                    "todavía no está configurada para esta automotora."
                )
            }, False
        if missing:
            return {
                "default_message": (
                    "Para simular tu financiamiento necesito "
                    + ", ".join(missing)
                    + "."
                )
            }, False

        simulation = calculate_financing(price, down_payment, installments, rate)
        return {"data": {"simulation": simulation}}, False

    if intent == Intent.DOWN_PAYMENT:
        minimum = automotive_settings.minimum_down_payment_pct if automotive_settings else None
        return {
            "data": {
                "minimum_down_payment_pct": minimum,
                "available_installments": automotive_settings.available_installments if automotive_settings else [],
            },
            "default_message": (
                "El pie y las condiciones dependen del vehículo y de la evaluación financiera. "
                "Puedo orientarte con el modelo y monto que tienes disponible."
            ),
        }, False

    if intent == Intent.CREDIT_REQUIREMENTS:
        return {
            "data": {
                "requirements": automotive_settings.credit_requirements if automotive_settings else []
            },
            "default_message": (
                "Los requisitos pueden variar según la entidad financiera y tu situación laboral. "
                "La aprobación queda sujeta a evaluación."
            ),
        }, False

    if intent == Intent.TEST_DRIVE:
        return {
            "data": {
                "test_drive_url": automotive_settings.test_drive_url if automotive_settings else None,
                "datetime_requested": extracted.datetime_requested,
            }
        }, False

    if intent == Intent.TRADE_IN:
        return {
            "data": {
                "trade_in_url": automotive_settings.trade_in_url if automotive_settings else None,
                "brand": extracted.trade_in_brand,
                "model": extracted.trade_in_model,
                "year": extracted.trade_in_year,
                "mileage_km": extracted.trade_in_mileage_km,
            }
        }, False

    if intent == Intent.MEDIA_REQUEST:
        vehicle = await get_vehicle(
            db,
            business.id,
            brand=extracted.brand,
            model=extracted.model,
            year=extracted.year,
        )
        return {
            "data": {
                "vehicle": vehicle,
                "media_type": extracted.media_type,
                "media_subject": extracted.media_subject,
            }
        }, False

    return {
        "default_message": (
            "Puedo ayudarte a buscar vehículos, revisar precios y stock, "
            "simular financiamiento o coordinar una prueba de manejo. ¿Qué estás buscando?"
        )
    }, False
