"""Carga una automotora demo con inventario, financiamiento y recursos multimedia.

Uso:
    python seed_automotive.py

El seed es idempotente por nombre y no crea duplicados si ya existe la automotora demo.
"""

import asyncio
import uuid

from sqlalchemy import select

from app.db.database import AsyncSessionLocal, init_db
from app.db.models import (
    AutomotiveSettings,
    Business,
    BusinessSettings,
    BusinessType,
    Vehicle,
)


BUSINESS_NAME = "Automotora Ejecutiva"
WELCOME_MESSAGE = (
    "¡Hola! 👋 Te damos la bienvenida a *Automotora Ejecutiva*.\n\n"
    "Soy el asistente encargado de apoyarte en la evaluación de tu próximo vehículo. "
    "Puedo ayudarte a revisar modelos, precios, disponibilidad y alternativas de financiamiento.\n\n"
    "¿Qué vehículo estás buscando?"
)


VEHICLES = [
    {
        "brand": "DFSK",
        "model": "600",
        "version": "Elite",
        "year": 2027,
        "body_type": "SUV",
        "transmission": "automática",
        "fuel_type": "gasolina",
        "color": "blanco",
        "price": 19190000,
        "mileage_km": 0,
        "stock_quantity": 2,
        "branch": "Santiago Centro",
        "description": "SUV familiar automática con cámara de retroceso y pantalla multimedia.",
        "specifications": {
            "engine": "1.5 Turbo",
            "power": "156 HP",
            "seats": 7,
            "air_conditioning": "climatizador",
        },
        "media": {
            "images": [
                "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7"
            ],
            "video": "https://www.w3schools.com/html/mov_bbb.mp4",
        },
        "detail_url": "https://example.com/vehiculos/dfsk-600",
    },
    {
        "brand": "Suzuki",
        "model": "Swift",
        "version": "GLX",
        "year": 2024,
        "body_type": "hatchback",
        "transmission": "manual",
        "fuel_type": "gasolina",
        "color": "rojo",
        "price": 10990000,
        "mileage_km": 12000,
        "stock_quantity": 1,
        "branch": "Santiago Centro",
        "description": "Hatchback compacto, económico y equipado para uso urbano.",
        "specifications": {
            "engine": "1.2",
            "power": "82 HP",
            "seats": 5,
            "air_conditioning": "manual",
        },
        "media": {
            "images": [
                "https://images.unsplash.com/photo-1503736334956-4c8f8e92946d"
            ],
            "video": "https://www.w3schools.com/html/mov_bbb.mp4",
        },
        "detail_url": "https://example.com/vehiculos/suzuki-swift",
    },
    {
        "brand": "Toyota",
        "model": "RAV4",
        "version": "XLE",
        "year": 2023,
        "body_type": "SUV",
        "transmission": "automática",
        "fuel_type": "híbrida",
        "color": "gris",
        "price": 22990000,
        "mileage_km": 28000,
        "stock_quantity": 1,
        "branch": "Las Condes",
        "description": "SUV híbrida con amplio espacio interior y asistencia de conducción.",
        "specifications": {
            "engine": "2.5 Hybrid",
            "power": "219 HP",
            "seats": 5,
            "drive": "AWD",
        },
        "media": {
            "images": [
                "https://images.unsplash.com/photo-1542362567-b07e54358753"
            ],
            "video": "https://www.w3schools.com/html/mov_bbb.mp4",
        },
        "detail_url": "https://example.com/vehiculos/toyota-rav4",
    },
]


async def seed() -> None:
    await init_db()
    async with AsyncSessionLocal() as db:
        existing = await db.scalar(
            select(Business).where(
                Business.name.in_([BUSINESS_NAME, "Automotora Demo"])
            )
        )
        if existing:
            if existing.name != BUSINESS_NAME:
                existing.name = BUSINESS_NAME
                existing.welcome_message = WELCOME_MESSAGE
                await db.commit()
            print(f"ℹ️  La automotora demo ya existe: {existing.id}")
            return

        business_id = str(uuid.uuid4())
        db.add(
            Business(
                id=business_id,
                name=BUSINESS_NAME,
                phone_number_id="AUTOMOTIVE_DEMO_PHONE_ID",
                whatsapp_token="DEMO_TOKEN",
                business_type=BusinessType.AUTOMOTIVE,
                welcome_message=WELCOME_MESSAGE,
                human_support_phone="+56900000000",
                is_active=True,
            )
        )
        db.add(
            BusinessSettings(
                id=str(uuid.uuid4()),
                business_id=business_id,
                address="Av. Automotriz 1234",
                city="Santiago",
                maps_url="https://maps.google.com/?q=Av+Automotriz+1234+Santiago",
                hours={
                    "lunes a viernes": "09:00-19:00",
                    "sábado": "10:00-16:00",
                    "domingo": "Cerrado",
                },
                currency="CLP",
                currency_symbol="$",
            )
        )
        db.add(
            AutomotiveSettings(
                id=str(uuid.uuid4()),
                business_id=business_id,
                monthly_interest_rate=1.89,
                minimum_down_payment_pct=20.0,
                available_installments=[24, 36, 48],
                credit_requirements=[
                    "Cédula de identidad vigente",
                    "Acreditación de ingresos",
                    "Antigüedad laboral o continuidad de ingresos",
                ],
                test_drive_url="https://example.com/agendar-prueba",
                trade_in_url="https://example.com/tasacion",
                financing_disclaimer=(
                    "Simulación referencial. No incluye seguros, impuestos, "
                    "comisiones ni otros costos operacionales."
                ),
            )
        )
        for vehicle_data in VEHICLES:
            db.add(
                Vehicle(
                    id=str(uuid.uuid4()),
                    business_id=business_id,
                    **vehicle_data,
                )
            )

        await db.commit()
        print(f"✅ Automotora demo creada: {business_id}")
        print(f"🚗 Vehículos cargados: {len(VEHICLES)}")
        print("💳 Tasa referencial configurada: 1.89% mensual")


if __name__ == "__main__":
    asyncio.run(seed())
