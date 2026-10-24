"""Cálculos determinísticos para simulaciones de financiamiento automotriz."""

from decimal import Decimal, ROUND_HALF_UP


def calculate_financing(
    vehicle_price: int,
    down_payment: int,
    installments: int,
    monthly_interest_rate: Decimal | float | str,
) -> dict:
    """Calcula una cuota fija referencial, sin afirmar aprobación crediticia."""
    if vehicle_price <= 0:
        raise ValueError("El precio del vehículo debe ser mayor que cero")
    if not 0 <= down_payment <= vehicle_price:
        raise ValueError("El pie debe estar entre cero y el precio del vehículo")
    if installments <= 0:
        raise ValueError("El plazo debe ser mayor que cero")

    rate = Decimal(str(monthly_interest_rate))
    if rate < 0:
        raise ValueError("La tasa mensual no puede ser negativa")

    financed = Decimal(vehicle_price - down_payment)
    monthly_rate = rate / Decimal("100")
    if financed == 0:
        payment = Decimal("0")
    elif monthly_rate == 0:
        payment = financed / Decimal(installments)
    else:
        factor = (Decimal("1") + monthly_rate) ** installments
        payment = financed * (monthly_rate * factor) / (factor - Decimal("1"))

    payment = payment.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    total_payments = payment * installments

    return {
        "vehicle_price": vehicle_price,
        "down_payment": down_payment,
        "financed_amount": int(financed),
        "installments": installments,
        "monthly_interest_rate": str(rate),
        "estimated_monthly_payment": int(payment),
        "total_installments": int(total_payments),
        "estimated_interest": int(total_payments - financed),
        "is_illustrative": True,
    }
