"""
Script de prueba rápida para verificar conexión a Groq API
"""
import asyncio
import os
import sys
from openai import AsyncOpenAI

# Configuración Groq
GROQ_API_KEY = os.getenv("OLLAMA_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "openai/gpt-oss-20b"


async def test_groq():
    """Prueba simple de Groq API"""
    if not GROQ_API_KEY:
        print("❌ Falta la variable de entorno OLLAMA_API_KEY")
        return False

    print("🔄 Probando conexión a Groq API...")
    print(f"   Modelo: {GROQ_MODEL}")
    print(f"   Base URL: {GROQ_BASE_URL}")
    print()
    
    client = AsyncOpenAI(
        base_url=GROQ_BASE_URL,
        api_key=GROQ_API_KEY,
        timeout=30.0,
        max_retries=2,
    )
    
    try:
        import time
        start_time = time.time()
        
        response = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system", 
                    "content": "Eres un asistente legal amigable. Responde en español de forma breve."
                },
                {
                    "role": "user", 
                    "content": "¿Qué servicios legales ofreces?"
                },
            ],
            max_tokens=100,
            temperature=0.4,
        )
        
        elapsed_time = time.time() - start_time
        response_text = response.choices[0].message.content.strip()
        
        print("✅ CONEXIÓN EXITOSA A GROQ")
        print(f"⏱️  Tiempo de respuesta: {elapsed_time:.2f} segundos")
        print(f"📝 Respuesta:\n{response_text}")
        print()
        print("🎉 ¡Groq está funcionando perfectamente!")
        return True
        
    except Exception as e:
        print(f"❌ ERROR conectando a Groq:")
        print(f"   {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_groq())
    sys.exit(0 if success else 1)
