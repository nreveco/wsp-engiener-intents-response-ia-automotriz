"""Pruebas unitarias del dominio automotriz sin WhatsApp ni base de datos."""

import unittest
from decimal import Decimal

from app.intents.definitions import ExtractedIntent, Intent
from app.intents.automotive_vocabulary import (
    AUTOMOTIVE_ENTITY_VOCABULARY,
    AUTOMOTIVE_INTENT_KEYWORDS,
    render_automotive_context_rules,
)
from app.prompts.templates import build_intent_prompt
from app.services.financing import calculate_financing


class FinancingTests(unittest.TestCase):
    def test_calculates_fixed_payment(self):
        result = calculate_financing(
            vehicle_price=15_000_000,
            down_payment=5_000_000,
            installments=48,
            monthly_interest_rate=Decimal("1.0"),
        )

        self.assertEqual(result["financed_amount"], 10_000_000)
        self.assertEqual(result["estimated_monthly_payment"], 263_338)
        self.assertTrue(result["is_illustrative"])

    def test_rejects_down_payment_above_vehicle_price(self):
        with self.assertRaises(ValueError):
            calculate_financing(10_000_000, 11_000_000, 48, Decimal("1.0"))

    def test_zero_interest_is_simple_division(self):
        result = calculate_financing(12_000_000, 3_000_000, 36, Decimal("0"))
        self.assertEqual(result["estimated_monthly_payment"], 250_000)


class AutomotiveIntentTests(unittest.TestCase):
    def test_extracts_combined_financing_and_media_request(self):
        extracted = ExtractedIntent.model_validate({
            "intent": "FINANCING_QUOTE",
            "secondary_intents": ["MEDIA_REQUEST"],
            "brand": "DFSK",
            "model": "600",
            "year": 2025,
            "transmission": "automatic",
            "vehicle_price": 15_000_000,
            "down_payment": 5_000_000,
            "installments": 48,
            "financing_requested": True,
            "media_type": "images",
        })

        self.assertEqual(extracted.intent, Intent.FINANCING_QUOTE)
        self.assertEqual(extracted.secondary_intents, [Intent.MEDIA_REQUEST])
        self.assertEqual(extracted.down_payment, 5_000_000)

    def test_prompt_prioritizes_real_catalog_data(self):
        prompt = build_intent_prompt("Automotora Demo", "automotive", ["SUV"])
        self.assertIn("VEHICLE_SEARCH", prompt)
        self.assertIn("No inventes una tasa", prompt)
        self.assertIn("precio confirmado del catálogo", prompt)
        self.assertIn("hasta", prompt)
        self.assertIn("prueba de manejo", prompt)
        self.assertIn("parte de pago", prompt)

    def test_vocabulary_covers_greeting_and_farewell(self):
        self.assertIn("buenos días", AUTOMOTIVE_INTENT_KEYWORDS[Intent.GREETING])
        self.assertIn("adiós", AUTOMOTIVE_INTENT_KEYWORDS[Intent.THANKS])
        self.assertIn("hasta luego", AUTOMOTIVE_INTENT_KEYWORDS[Intent.THANKS])

    def test_vocabulary_covers_chilean_entities_and_context(self):
        self.assertIn("palos", AUTOMOTIVE_ENTITY_VOCABULARY["amount_units"])
        self.assertIn("retoma", AUTOMOTIVE_ENTITY_VOCABULARY["trade_in_terms"])
        self.assertIn("cámara de retroceso", AUTOMOTIVE_ENTITY_VOCABULARY["vehicle_features"])
        self.assertIn("cuota o meses implica FINANCING_QUOTE", render_automotive_context_rules())

    def test_prompt_includes_humanized_response_guidance(self):
        prompt = build_intent_prompt("Automotora Ejecutiva", "automotive", [])
        self.assertIn("errores de escritura", prompt)
        self.assertIn("secondary_intents", prompt)


if __name__ == "__main__":
    unittest.main()
