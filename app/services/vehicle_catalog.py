"""Consultas del catálogo automotriz, siempre acotadas al negocio."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Vehicle


def _vehicle_data(vehicle: Vehicle) -> dict:
    return {
        "id": vehicle.id,
        "brand": vehicle.brand,
        "model": vehicle.model,
        "version": vehicle.version,
        "year": vehicle.year,
        "body_type": vehicle.body_type,
        "transmission": vehicle.transmission,
        "fuel_type": vehicle.fuel_type,
        "color": vehicle.color,
        "price": vehicle.price,
        "mileage_km": vehicle.mileage_km,
        "stock_quantity": vehicle.stock_quantity,
        "branch": vehicle.branch,
        "description": vehicle.description,
        "specifications": vehicle.specifications or {},
        "media": vehicle.media or {},
        "detail_url": vehicle.detail_url,
        "is_available": vehicle.is_available and (vehicle.stock_quantity or 0) > 0,
    }


async def search_vehicles(
    db: AsyncSession,
    business_id: str,
    *,
    brand: Optional[str] = None,
    model: Optional[str] = None,
    body_type: Optional[str] = None,
    transmission: Optional[str] = None,
    year: Optional[int] = None,
    color: Optional[str] = None,
    max_budget: Optional[int] = None,
    limit: int = 10,
) -> list[dict]:
    """Busca vehículos disponibles; nunca devuelve inventario de otro negocio."""
    filters = [
        Vehicle.business_id == business_id,
        Vehicle.is_available.is_(True),
        Vehicle.stock_quantity > 0,
    ]
    for column, value in (
        (Vehicle.brand, brand),
        (Vehicle.model, model),
        (Vehicle.body_type, body_type),
        (Vehicle.transmission, transmission),
        (Vehicle.color, color),
    ):
        if value:
            filters.append(column.ilike(f"%{value}%"))
    if year:
        filters.append(Vehicle.year == year)
    if max_budget is not None:
        filters.append(Vehicle.price <= max_budget)

    result = await db.execute(
        select(Vehicle).where(*filters).order_by(Vehicle.price.asc()).limit(limit)
    )
    return [_vehicle_data(vehicle) for vehicle in result.scalars().all()]


async def get_vehicle(
    db: AsyncSession,
    business_id: str,
    *,
    vehicle_id: Optional[str] = None,
    brand: Optional[str] = None,
    model: Optional[str] = None,
    year: Optional[int] = None,
) -> Optional[dict]:
    filters = [Vehicle.business_id == business_id]
    if vehicle_id:
        filters.append(Vehicle.id == vehicle_id)
    if brand:
        filters.append(Vehicle.brand.ilike(f"%{brand}%"))
    if model:
        filters.append(Vehicle.model.ilike(f"%{model}%"))
    if year:
        filters.append(Vehicle.year == year)

    result = await db.execute(select(Vehicle).where(*filters).limit(1))
    vehicle = result.scalar_one_or_none()
    return _vehicle_data(vehicle) if vehicle else None
