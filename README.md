# Bot automotriz WhatsApp

Asistente comercial para automotoras basado en WhatsApp Cloud API, FastAPI,
PostgreSQL y modelos compatibles con la API de OpenAI (Ollama local o proveedor
externo configurado).

El bot puede buscar vehículos, entregar fichas verificadas, consultar stock,
simular financiamiento, orientar sobre crédito, coordinar pruebas de manejo,
recibir solicitudes de parte de pago y entregar recursos multimedia del catálogo.

## Arquitectura

```text
WhatsApp / Meta Cloud API
            |
            v
     FastAPI / webhook
            |
   +--------+---------+
   |                  |
   v                  v
Procesador media   Clasificador IA
audio/imagen/PDF   intención + entidades
                         |
                         v
                 Router automotriz
             acciones determinísticas
                         |
       +-----------------+-----------------+
       |                 |                 |
       v                 v                 v
   Catálogo        Financiamiento      Conversación
   PostgreSQL      fórmula fija        por teléfono
                         |
                         v
                 Generador de respuesta
                         |
                         v
                    WhatsApp
```

La IA clasifica y extrae datos, pero no inventa precios, stock, tasas, cuotas,
promociones ni URLs. El catálogo y el módulo financiero son la fuente de verdad.

## Intenciones automotrices

- `VEHICLE_SEARCH`
- `VEHICLE_DETAILS`
- `VEHICLE_PRICE`
- `FINANCING_QUOTE`
- `DOWN_PAYMENT`
- `CREDIT_REQUIREMENTS`
- `VEHICLE_AVAILABILITY`
- `TEST_DRIVE`
- `TRADE_IN`
- `MEDIA_REQUEST`

También se mantienen intenciones generales como `GREETING`, `THANKS`,
`HUMAN_SUPPORT`, `HOURS_QUERY` y `LOCATION_QUERY`.

Un mismo mensaje puede tener una intención principal y secundarias. Por ejemplo,
una consulta de financiamiento que también solicita fotos se representa como:

```json
{
  "intent": "FINANCING_QUOTE",
  "secondary_intents": ["MEDIA_REQUEST"],
  "brand": "DFSK",
  "model": "600",
  "vehicle_price": 15000000,
  "down_payment": 5000000,
  "installments": 48
}
```

## Memoria conversacional

La memoria se asocia a:

```text
business_id + número de WhatsApp del cliente
```

Se conserva el historial de mensajes y un contexto de financiamiento:

```json
{
  "financing": {
    "vehicle_price": 15000000,
    "down_payment": 5000000,
    "installments": 48
  },
  "selected_vehicle": {
    "id": "...",
    "price": 15000000
  }
}
```

Esto permite que el cliente escriba:

```text
El auto cuesta 15 millones, tengo 5 millones de pie
```

y luego:

```text
Mejor calcúlalo a 48 meses
```

sin repetir el resto de los datos.

## Financiamiento

El simulador usa amortización de cuota fija y recibe la tasa desde la
configuración de la automotora. La IA nunca determina la tasa.

```python
from decimal import Decimal
from app.services.financing import calculate_financing

calculate_financing(
    vehicle_price=15_000_000,
    down_payment=5_000_000,
    installments=48,
    monthly_interest_rate=Decimal("1.0"),
)
```

El resultado es referencial e incluye:

- Monto financiado.
- Cuota mensual estimada.
- Total de cuotas.
- Intereses estimados.
- Indicador de simulación ilustrativa.

No reemplaza una cotización financiera formal ni incluye necesariamente seguros,
impuestos, comisiones, gastos operacionales o cuota final.

## Inicio rápido

### Docker

```powershell
Copy-Item .env.example .env
# Completar credenciales en .env
.\docker-rebuild.cmd
```

Servicios principales:

- FastAPI: `http://localhost`
- Documentación: `http://localhost/docs`
- PostgreSQL: `localhost:5432`
- Ollama: `http://localhost:11434`

### Desarrollo local

Se recomienda Python 3.12 para las versiones fijadas en `requirements.txt`.

```powershell
python -m venv venv
.\venv\Scripts\activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Seed automotriz

El seed crea una automotora demo con:

- Configuración de financiamiento al 1% mensual.
- Pie mínimo referencial de 20%.
- Plazos de 24, 36, 48 y 60 cuotas.
- Requisitos de crédito.
- URL de prueba de manejo.
- URL de tasación.
- Tres vehículos demo.
- Especificaciones, stock, precio, sucursal, ficha y multimedia.

```powershell
python seed_automotive.py
```

El seed es idempotente por nombre y no duplica la automotora demo.

## API administrativa automotriz

Todos los endpoints requieren:

```text
X-Admin-Key: <ADMIN_API_KEY>
```

### Configuración

```text
GET /admin/businesses/{business_id}/automotive-settings
PUT /admin/businesses/{business_id}/automotive-settings
```

### Vehículos

```text
POST   /admin/businesses/{business_id}/vehicles
GET    /admin/businesses/{business_id}/vehicles
PATCH  /admin/businesses/{business_id}/vehicles/{vehicle_id}
DELETE /admin/businesses/{business_id}/vehicles/{vehicle_id}
```

El listado permite filtrar únicamente vehículos disponibles:

```text
GET /admin/businesses/{business_id}/vehicles?available_only=true
```

## Pruebas

Pruebas unitarias del dominio automotriz:

```powershell
python -m unittest test_automotive.py
```

Validación sintáctica:

```powershell
python -m compileall -q app
```

## Variables de entorno principales

| Variable | Descripción |
|---|---|
| `DATABASE_URL` | PostgreSQL con `postgresql+asyncpg://` |
| `OLLAMA_BASE_URL` | API compatible con OpenAI |
| `OLLAMA_MODEL` | Modelo de clasificación y redacción |
| `OLLAMA_VISION_MODEL` | Modelo de visión |
| `WHATSAPP_TOKEN` | Token de Meta Cloud API |
| `WHATSAPP_PHONE_NUMBER_ID` | Número configurado en Meta |
| `WHATSAPP_VERIFY_TOKEN` | Token de verificación |
| `ADMIN_API_KEY` | Clave de la API administrativa |

## Estructura relevante

```text
app/
├── ai/
│   ├── intent_classifier.py
│   ├── media_processor.py
│   └── response_builder.py
├── db/
│   ├── database.py
│   └── models.py
├── intents/
│   └── definitions.py
├── routers/
│   ├── admin.py
│   ├── webhook.py
│   └── webhook_automotive_route.py
├── services/
│   ├── financing.py
│   └── vehicle_catalog.py
└── prompts/
    └── templates.py
```

## Criterios comerciales

- El precio del cliente no se considera precio oficial sin validarlo en catálogo.
- El stock se consulta por negocio, modelo, año, color y sucursal.
- La tasa financiera debe estar configurada por la automotora.
- Una simulación nunca implica aprobación crediticia.
- El bot no inventa recursos multimedia.
- El contexto se conserva por número de cliente dentro de cada negocio.
