-- WhatsApp AI Automation - esquema PostgreSQL para Railway
-- Basado en app/db/models.py
--
-- IMPORTANTE:
-- Este script elimina las tablas y tipos existentes del mismo esquema.
-- Ejecutarlo solo en una base nueva o cuando se acepte perder esos datos.
-- No contiene tokens, credenciales ni datos demo.

BEGIN;

DROP TABLE IF EXISTS quote_items CASCADE;
DROP TABLE IF EXISTS quotes CASCADE;
DROP TABLE IF EXISTS leads CASCADE;
DROP TABLE IF EXISTS bookings CASCADE;
DROP TABLE IF EXISTS case_inquiries CASCADE;
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS conversations CASCADE;
DROP TABLE IF EXISTS vehicles CASCADE;
DROP TABLE IF EXISTS automotive_settings CASCADE;
DROP TABLE IF EXISTS fee_structures CASCADE;
DROP TABLE IF EXISTS legal_services CASCADE;
DROP TABLE IF EXISTS legal_categories CASCADE;
DROP TABLE IF EXISTS business_settings CASCADE;
DROP TABLE IF EXISTS businesses CASCADE;

DROP TYPE IF EXISTS caseinquirystatus CASCADE;
DROP TYPE IF EXISTS caseurgency CASCADE;
DROP TYPE IF EXISTS legalarea CASCADE;
DROP TYPE IF EXISTS quotestatus CASCADE;
DROP TYPE IF EXISTS bookingstatus CASCADE;
DROP TYPE IF EXISTS conversationstatus CASCADE;
DROP TYPE IF EXISTS businesstype CASCADE;

CREATE TYPE businesstype AS ENUM (
    'automotive',
    'restaurant',
    'cafe',
    'shop',
    'workshop',
    'clinic',
    'construction',
    'liquor_store',
    'law_firm',
    'other'
);

CREATE TYPE conversationstatus AS ENUM (
    'active',
    'human_handoff',
    'closed'
);

CREATE TYPE bookingstatus AS ENUM (
    'pending',
    'confirmed',
    'cancelled'
);

CREATE TYPE quotestatus AS ENUM (
    'draft',
    'sent',
    'accepted',
    'rejected'
);

CREATE TYPE legalarea AS ENUM (
    'penal',
    'familia',
    'civil'
);

CREATE TYPE caseurgency AS ENUM (
    'low',
    'medium',
    'high'
);

CREATE TYPE caseinquirystatus AS ENUM (
    'pending',
    'in_review',
    'accepted',
    'rejected',
    'closed'
);

CREATE TABLE businesses (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    phone_number_id VARCHAR(50) UNIQUE NOT NULL,
    whatsapp_token VARCHAR(500) NOT NULL,
    business_type businesstype DEFAULT 'other',
    welcome_message TEXT,
    human_support_phone VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE business_settings (
    id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) UNIQUE NOT NULL
        REFERENCES businesses(id) ON DELETE CASCADE,
    address VARCHAR(500),
    city VARCHAR(100),
    maps_url VARCHAR(500),
    hours JSONB DEFAULT '{}'::jsonb,
    currency VARCHAR(10) DEFAULT 'CLP',
    currency_symbol VARCHAR(5) DEFAULT '$'
);

-- Configuración propia de una automotora.
CREATE TABLE automotive_settings (
    id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) UNIQUE NOT NULL
        REFERENCES businesses(id) ON DELETE CASCADE,
    monthly_interest_rate DOUBLE PRECISION,
    minimum_down_payment_pct DOUBLE PRECISION,
    available_installments JSONB DEFAULT '[]'::jsonb,
    credit_requirements JSONB DEFAULT '[]'::jsonb,
    test_drive_url VARCHAR(500),
    trade_in_url VARCHAR(500),
    financing_disclaimer TEXT
);

-- Inventario y recursos multimedia de cada vehículo.
CREATE TABLE vehicles (
    id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL
        REFERENCES businesses(id) ON DELETE CASCADE,
    brand VARCHAR(100) NOT NULL,
    model VARCHAR(150) NOT NULL,
    version VARCHAR(150),
    year INTEGER,
    body_type VARCHAR(80),
    transmission VARCHAR(50),
    fuel_type VARCHAR(50),
    color VARCHAR(80),
    price INTEGER NOT NULL,
    mileage_km INTEGER,
    stock_quantity INTEGER DEFAULT 1,
    branch VARCHAR(150),
    description TEXT,
    specifications JSONB DEFAULT '{}'::jsonb,
    media JSONB DEFAULT '{}'::jsonb,
    detail_url VARCHAR(500),
    is_available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE legal_categories (
    id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL
        REFERENCES businesses(id) ON DELETE CASCADE,
    area legalarea NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE legal_services (
    id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL
        REFERENCES businesses(id) ON DELETE CASCADE,
    category_id VARCHAR(36)
        REFERENCES legal_categories(id) ON DELETE SET NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    base_price DOUBLE PRECISION,
    estimated_timeframe VARCHAR(100),
    requirements TEXT,
    is_available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE fee_structures (
    id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL
        REFERENCES businesses(id) ON DELETE CASCADE,
    service_type VARCHAR(200) NOT NULL,
    description TEXT,
    min_price DOUBLE PRECISION,
    max_price DOUBLE PRECISION,
    payment_options JSONB DEFAULT '[]'::jsonb,
    payment_facilities TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE conversations (
    id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL
        REFERENCES businesses(id) ON DELETE CASCADE,
    customer_phone VARCHAR(50) NOT NULL,
    customer_name VARCHAR(200),
    status conversationstatus DEFAULT 'active',
    context JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE messages (
    id VARCHAR(36) PRIMARY KEY,
    conversation_id VARCHAR(36) NOT NULL
        REFERENCES conversations(id) ON DELETE CASCADE,
    direction VARCHAR(10) NOT NULL,
    content TEXT NOT NULL,
    intent VARCHAR(50),
    wa_message_id VARCHAR(100) UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE case_inquiries (
    id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL
        REFERENCES businesses(id) ON DELETE CASCADE,
    customer_phone VARCHAR(50) NOT NULL,
    customer_name VARCHAR(200),
    legal_area legalarea,
    legal_matter VARCHAR(200),
    description TEXT,
    urgency caseurgency DEFAULT 'medium',
    is_detained BOOLEAN DEFAULT FALSE,
    has_prior_record BOOLEAN,
    benefit_type VARCHAR(200),
    status caseinquirystatus DEFAULT 'pending',
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE bookings (
    id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL
        REFERENCES businesses(id) ON DELETE CASCADE,
    customer_phone VARCHAR(50) NOT NULL,
    customer_name VARCHAR(200),
    datetime_requested VARCHAR(200),
    datetime_confirmed TIMESTAMP WITH TIME ZONE,
    service VARCHAR(200),
    notes TEXT,
    status bookingstatus DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE leads (
    id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL
        REFERENCES businesses(id) ON DELETE CASCADE,
    phone VARCHAR(50) NOT NULL,
    name VARCHAR(200),
    first_intent VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE quotes (
    id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL
        REFERENCES businesses(id) ON DELETE CASCADE,
    customer_phone VARCHAR(50) NOT NULL,
    customer_name VARCHAR(200),
    description TEXT NOT NULL,
    notes TEXT,
    status quotestatus DEFAULT 'draft',
    total DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE quote_items (
    id VARCHAR(36) PRIMARY KEY,
    quote_id VARCHAR(36) NOT NULL
        REFERENCES quotes(id) ON DELETE CASCADE,
    description VARCHAR(300) NOT NULL,
    quantity INTEGER DEFAULT 1,
    unit_price DOUBLE PRECISION NOT NULL
);

CREATE INDEX idx_businesses_phone ON businesses(phone_number_id);
CREATE INDEX idx_conversations_business ON conversations(business_id);
CREATE INDEX idx_conversations_customer ON conversations(business_id, customer_phone);
CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_created ON messages(created_at);
CREATE INDEX idx_case_inquiries_business ON case_inquiries(business_id);
CREATE INDEX idx_case_inquiries_status ON case_inquiries(status);
CREATE INDEX idx_case_inquiries_phone ON case_inquiries(customer_phone);
CREATE INDEX idx_bookings_business ON bookings(business_id);
CREATE INDEX idx_bookings_status ON bookings(status);
CREATE INDEX idx_leads_business ON leads(business_id);
CREATE INDEX idx_quotes_business ON quotes(business_id);
CREATE INDEX idx_legal_services_business ON legal_services(business_id);
CREATE INDEX idx_legal_categories_business ON legal_categories(business_id);
CREATE INDEX idx_vehicles_business ON vehicles(business_id);
CREATE INDEX idx_vehicles_search ON vehicles(business_id, brand, model, year);
CREATE INDEX idx_vehicles_available ON vehicles(business_id, is_available);

COMMIT;

-- Verificación posterior:
-- SELECT table_name
-- FROM information_schema.tables
-- WHERE table_schema = 'public'
-- ORDER BY table_name;
--
-- SELECT id, name, business_type, phone_number_id
-- FROM businesses;
