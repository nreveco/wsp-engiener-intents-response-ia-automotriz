-- Seed demo automotriz para Railway
-- Ejecutar DESPUÉS de railway-init.sql.
--
-- Este script es idempotente usando IDs fijos.
-- Reemplaza DEMO_TOKEN y AUTOMOTIVE_DEMO_PHONE_ID por valores reales
-- antes de usarlo con un número de WhatsApp productivo.

BEGIN;

INSERT INTO businesses (
    id,
    name,
    phone_number_id,
    whatsapp_token,
    business_type,
    welcome_message,
    human_support_phone,
    is_active
)
VALUES (
    'automotive-demo-business-001',
    'Automotora Ejecutiva',
    'AUTOMOTIVE_DEMO_PHONE_ID',
    'DEMO_TOKEN',
    'automotive',
    E'¡Hola! 👋 Te damos la bienvenida a *Automotora Ejecutiva*.\n\n'
    'Soy el asistente encargado de apoyarte en la evaluación de tu próximo vehículo. '
    'Puedo ayudarte a revisar modelos, precios, disponibilidad y alternativas de financiamiento.\n\n'
    '¿Qué vehículo estás buscando?',
    '+56900000000',
    TRUE
)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    phone_number_id = EXCLUDED.phone_number_id,
    whatsapp_token = EXCLUDED.whatsapp_token,
    business_type = EXCLUDED.business_type,
    welcome_message = EXCLUDED.welcome_message,
    human_support_phone = EXCLUDED.human_support_phone,
    is_active = EXCLUDED.is_active;

INSERT INTO business_settings (
    id,
    business_id,
    address,
    city,
    maps_url,
    hours,
    currency,
    currency_symbol
)
VALUES (
    'automotive-demo-settings-001',
    'automotive-demo-business-001',
    'Av. Automotriz 1234',
    'Santiago',
    'https://maps.google.com/?q=Av+Automotriz+1234+Santiago',
    $json$
    {
        "lunes a viernes": "09:00-19:00",
        "sábado": "10:00-16:00",
        "domingo": "Cerrado"
    }
    $json$::jsonb,
    'CLP',
    '$'
)
ON CONFLICT (id) DO UPDATE SET
    business_id = EXCLUDED.business_id,
    address = EXCLUDED.address,
    city = EXCLUDED.city,
    maps_url = EXCLUDED.maps_url,
    hours = EXCLUDED.hours,
    currency = EXCLUDED.currency,
    currency_symbol = EXCLUDED.currency_symbol;

INSERT INTO automotive_settings (
    id,
    business_id,
    monthly_interest_rate,
    minimum_down_payment_pct,
    available_installments,
    credit_requirements,
    test_drive_url,
    trade_in_url,
    financing_disclaimer
)
VALUES (
    'automotive-demo-financing-001',
    'automotive-demo-business-001',
    1.89,
    20.0,
    '[24, 36, 48]'::jsonb,
    $json$
    [
        "Cédula de identidad vigente",
        "Acreditación de ingresos",
        "Antigüedad laboral o continuidad de ingresos"
    ]
    $json$::jsonb,
    'https://example.com/agendar-prueba',
    'https://example.com/tasacion',
    'Simulación referencial. No incluye seguros, impuestos, comisiones ni otros costos operacionales.'
)
ON CONFLICT (id) DO UPDATE SET
    business_id = EXCLUDED.business_id,
    monthly_interest_rate = EXCLUDED.monthly_interest_rate,
    minimum_down_payment_pct = EXCLUDED.minimum_down_payment_pct,
    available_installments = EXCLUDED.available_installments,
    credit_requirements = EXCLUDED.credit_requirements,
    test_drive_url = EXCLUDED.test_drive_url,
    trade_in_url = EXCLUDED.trade_in_url,
    financing_disclaimer = EXCLUDED.financing_disclaimer;

INSERT INTO vehicles (
    id,
    business_id,
    brand,
    model,
    version,
    year,
    body_type,
    transmission,
    fuel_type,
    color,
    price,
    mileage_km,
    stock_quantity,
    branch,
    description,
    specifications,
    media,
    detail_url,
    is_available
)
VALUES
(
    'automotive-demo-vehicle-001',
    'automotive-demo-business-001',
    'DFSK',
    '600',
    'Elite',
    2027,
    'SUV',
    'automática',
    'gasolina',
    'blanco',
    19190000,
    0,
    2,
    'Santiago Centro',
    'SUV familiar automática con cámara de retroceso y pantalla multimedia.',
    $json$
    {
        "engine": "1.5 Turbo",
        "power": "156 HP",
        "seats": 7,
        "air_conditioning": "climatizador"
    }
    $json$::jsonb,
    $json$
    {
        "images": [
            "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7"
        ],
        "video": "https://www.w3schools.com/html/mov_bbb.mp4"
    }
    $json$::jsonb,
    'https://example.com/vehiculos/dfsk-600',
    TRUE
),
(
    'automotive-demo-vehicle-002',
    'automotive-demo-business-001',
    'Suzuki',
    'Swift',
    'GLX',
    2024,
    'hatchback',
    'manual',
    'gasolina',
    'rojo',
    10990000,
    12000,
    1,
    'Santiago Centro',
    'Hatchback compacto, económico y equipado para uso urbano.',
    $json$
    {
        "engine": "1.2",
        "power": "82 HP",
        "seats": 5,
        "air_conditioning": "manual"
    }
    $json$::jsonb,
    $json$
    {
        "images": [
            "https://images.unsplash.com/photo-1503736334956-4c8f8e92946d"
        ],
        "video": "https://www.w3schools.com/html/mov_bbb.mp4"
    }
    $json$::jsonb,
    'https://example.com/vehiculos/suzuki-swift',
    TRUE
),
(
    'automotive-demo-vehicle-003',
    'automotive-demo-business-001',
    'Toyota',
    'RAV4',
    'XLE',
    2023,
    'SUV',
    'automática',
    'híbrida',
    'gris',
    22990000,
    28000,
    1,
    'Las Condes',
    'SUV híbrida con amplio espacio interior y asistencia de conducción.',
    $json$
    {
        "engine": "2.5 Hybrid",
        "power": "219 HP",
        "seats": 5,
        "drive": "AWD"
    }
    $json$::jsonb,
    $json$
    {
        "images": [
            "https://images.unsplash.com/photo-1542362567-b07e54358753"
        ],
        "video": "https://www.w3schools.com/html/mov_bbb.mp4"
    }
    $json$::jsonb,
    'https://example.com/vehiculos/toyota-rav4',
    TRUE
)
ON CONFLICT (id) DO UPDATE SET
    business_id = EXCLUDED.business_id,
    brand = EXCLUDED.brand,
    model = EXCLUDED.model,
    version = EXCLUDED.version,
    year = EXCLUDED.year,
    body_type = EXCLUDED.body_type,
    transmission = EXCLUDED.transmission,
    fuel_type = EXCLUDED.fuel_type,
    color = EXCLUDED.color,
    price = EXCLUDED.price,
    mileage_km = EXCLUDED.mileage_km,
    stock_quantity = EXCLUDED.stock_quantity,
    branch = EXCLUDED.branch,
    description = EXCLUDED.description,
    specifications = EXCLUDED.specifications,
    media = EXCLUDED.media,
    detail_url = EXCLUDED.detail_url,
    is_available = EXCLUDED.is_available;

COMMIT;

-- Verificación:
-- SELECT id, name, business_type, phone_number_id
-- FROM businesses
-- WHERE id = 'automotive-demo-business-001';
--
-- SELECT brand, model, year, price, stock_quantity, is_available
-- FROM vehicles
-- WHERE business_id = 'automotive-demo-business-001'
-- ORDER BY brand, model;
