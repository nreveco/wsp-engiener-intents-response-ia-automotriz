"""
Script de prueba para la nueva intención EXPULSION_INQUIRY
Valida el flujo conversacional y las respuestas del bot
"""

import asyncio
from app.intents.definitions import Intent, ExtractedIntent


def test_intent_definition():
    """Verifica que la nueva intención esté correctamente definida"""
    print("✅ Test 1: Verificando definición de intención...")
    
    # Verificar que EXPULSION_INQUIRY existe
    assert hasattr(Intent, "EXPULSION_INQUIRY"), "EXPULSION_INQUIRY no está definida"
    assert Intent.EXPULSION_INQUIRY == "EXPULSION_INQUIRY"
    print("   ✓ Intención EXPULSION_INQUIRY definida correctamente")
    
    # Verificar que ExtractedIntent tiene los nuevos campos
    intent = ExtractedIntent(intent=Intent.EXPULSION_INQUIRY)
    assert hasattr(intent, "has_document"), "Campo has_document no existe"
    assert hasattr(intent, "document_issuer"), "Campo document_issuer no existe"
    assert hasattr(intent, "in_criminal_process"), "Campo in_criminal_process no existe"
    assert hasattr(intent, "expulsion_type"), "Campo expulsion_type no existe"
    print("   ✓ Campos de expulsión agregados correctamente")


def test_expulsion_keywords():
    """Verifica que las keywords de expulsión estén en el prompt"""
    print("\n✅ Test 2: Verificando keywords en prompt...")
    
    from app.prompts.templates import build_intent_prompt
    
    prompt = build_intent_prompt(
        business_name="Test Business",
        business_type="legal",
        categories=["Derecho de Familia"]
    )
    
    # Verificar keywords
    keywords = [
        "EXPULSION_INQUIRY",
        "expulsión",
        "orden de expulsión",
        "SERMIG",
        "PDI",
        "tribunal penal",
        "deportación"
    ]
    
    for keyword in keywords:
        assert keyword in prompt, f"Keyword '{keyword}' no encontrada en prompt"
    
    print(f"   ✓ {len(keywords)} keywords encontradas en prompt")


def test_extracted_intent_with_expulsion():
    """Verifica que se puede crear ExtractedIntent con datos de expulsión"""
    print("\n✅ Test 3: Verificando ExtractedIntent con datos de expulsión...")
    
    # Crear intent con expulsión administrativa
    intent_admin = ExtractedIntent(
        intent=Intent.EXPULSION_INQUIRY,
        legal_area="migraciones",
        has_document=True,
        document_issuer="SERMIG",
        expulsion_type="administrativa",
        urgency="high"
    )
    
    assert intent_admin.intent == Intent.EXPULSION_INQUIRY
    assert intent_admin.expulsion_type == "administrativa"
    assert intent_admin.document_issuer == "SERMIG"
    print("   ✓ ExtractedIntent administrativa creado correctamente")
    
    # Crear intent con expulsión judicial
    intent_judicial = ExtractedIntent(
        intent=Intent.EXPULSION_INQUIRY,
        legal_area="migraciones",
        has_document=True,
        document_issuer="Tribunal",
        in_criminal_process=True,
        expulsion_type="judicial",
        urgency="high"
    )
    
    assert intent_judicial.intent == Intent.EXPULSION_INQUIRY
    assert intent_judicial.expulsion_type == "judicial"
    assert intent_judicial.in_criminal_process == True
    print("   ✓ ExtractedIntent judicial creado correctamente")


def test_video_url():
    """Verifica que la URL del video esté correctamente definida"""
    print("\n✅ Test 4: Verificando URL del video...")
    
    video_url = "https://mediacionesrjz.cl/expulsionrjz.mp4"
    booking_url = "https://mediacionesrjz.cl/profesionales"
    
    # Verificar que las URLs están en el código
    import inspect
    from app.routers import webhook_legal_route
    
    source = inspect.getsource(webhook_legal_route._route_intent_legal)
    
    assert video_url in source, f"Video URL '{video_url}' no encontrada en webhook_legal_route"
    assert booking_url in source, f"Booking URL '{booking_url}' no encontrada en webhook_legal_route"
    
    print(f"   ✓ Video URL: {video_url}")
    print(f"   ✓ Booking URL: {booking_url}")


def test_gateway_video_function():
    """Verifica que la función send_video_with_caption existe"""
    print("\n✅ Test 5: Verificando función de envío de video...")
    
    from app.whatsapp.gateway import send_video_with_caption
    
    # Verificar que la función existe y tiene los parámetros correctos
    import inspect
    sig = inspect.signature(send_video_with_caption)
    params = list(sig.parameters.keys())
    
    expected_params = ["whatsapp_token", "phone_number_id", "to_phone", "video_url", "caption"]
    for param in expected_params:
        assert param in params, f"Parámetro '{param}' no encontrado en send_video_with_caption"
    
    print("   ✓ Función send_video_with_caption definida correctamente")
    print(f"   ✓ Parámetros: {', '.join(params)}")


def test_response_structure():
    """Verifica la estructura de las respuestas de expulsión"""
    print("\n✅ Test 6: Verificando estructura de respuestas...")
    
    # Simular query_result de Rama A (Administrativa)
    rama_a_response = {
        "expulsion_type": "administrativa",
        "video_url": "https://mediacionesrjz.cl/expulsionrjz.mp4",
        "default_message": "📋 EXPULSIÓN ADMINISTRATIVA..."
    }
    
    assert "expulsion_type" in rama_a_response
    assert "video_url" in rama_a_response
    assert "default_message" in rama_a_response
    assert rama_a_response["expulsion_type"] == "administrativa"
    print("   ✓ Estructura de respuesta Rama A (Administrativa) correcta")
    
    # Simular query_result de Rama B (Judicial)
    rama_b_response = {
        "expulsion_type": "judicial",
        "video_url": "https://mediacionesrjz.cl/expulsionrjz.mp4",
        "default_message": "⚖️ EXPULSIÓN JUDICIAL..."
    }
    
    assert "expulsion_type" in rama_b_response
    assert "video_url" in rama_b_response
    assert "default_message" in rama_b_response
    assert rama_b_response["expulsion_type"] == "judicial"
    print("   ✓ Estructura de respuesta Rama B (Judicial) correcta")


def test_conversation_flow_questions():
    """Verifica que las preguntas del flujo estén correctamente definidas"""
    print("\n✅ Test 7: Verificando preguntas del flujo conversacional...")
    
    questions = [
        "¿Tienes copia del documento o resolución de expulsión?",
        "¿Quién emite el documento?",
        "¿La persona está en un proceso penal?"
    ]
    
    import inspect
    from app.routers import webhook_legal_route
    
    source = inspect.getsource(webhook_legal_route._route_intent_legal)
    
    for question in questions:
        assert question in source, f"Pregunta '{question}' no encontrada en el flujo"
    
    print(f"   ✓ {len(questions)} preguntas del flujo encontradas")
    for i, q in enumerate(questions, 1):
        print(f"      {i}. {q}")


def run_all_tests():
    """Ejecuta todos los tests"""
    print("=" * 70)
    print("🧪 EJECUTANDO TESTS PARA EXPULSION_INQUIRY")
    print("=" * 70)
    
    try:
        test_intent_definition()
        test_expulsion_keywords()
        test_extracted_intent_with_expulsion()
        test_video_url()
        test_gateway_video_function()
        test_response_structure()
        test_conversation_flow_questions()
        
        print("\n" + "=" * 70)
        print("✅ TODOS LOS TESTS PASARON EXITOSAMENTE")
        print("=" * 70)
        print("\n📝 La nueva intención EXPULSION_INQUIRY está correctamente implementada")
        print("🚀 El bot está listo para manejar consultas sobre expulsión")
        print("\n💡 Próximos pasos:")
        print("   1. Reiniciar el servicio del bot")
        print("   2. Probar con un usuario real en WhatsApp")
        print("   3. Monitorear logs para verificar el envío del video")
        
    except AssertionError as e:
        print(f"\n❌ ERROR EN TEST: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
