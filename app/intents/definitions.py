import enum
from typing import Optional
from pydantic import BaseModel, Field


class Intent(str, enum.Enum):
    # ══════════════════════════════════════════════════════════
    # INTENCIONES AUTOMOTRICES
    # ══════════════════════════════════════════════════════════
    VEHICLE_SEARCH = "VEHICLE_SEARCH"
    VEHICLE_DETAILS = "VEHICLE_DETAILS"
    VEHICLE_PRICE = "VEHICLE_PRICE"
    FINANCING_QUOTE = "FINANCING_QUOTE"
    DOWN_PAYMENT = "DOWN_PAYMENT"
    CREDIT_REQUIREMENTS = "CREDIT_REQUIREMENTS"
    VEHICLE_AVAILABILITY = "VEHICLE_AVAILABILITY"
    TEST_DRIVE = "TEST_DRIVE"
    TRADE_IN = "TRADE_IN"
    MEDIA_REQUEST = "MEDIA_REQUEST"

    # ══════════════════════════════════════════════════════════
    # INTENCIONES LEGALES - ESTUDIO JURÍDICO
    # ══════════════════════════════════════════════════════════
    
    # Mantener (útiles para contexto legal)
    GREETING = "GREETING"              # Hola / buenos días / quiero información
    THANKS = "THANKS"                  # Gracias / muchas gracias / perfecto gracias
    BOOKING = "BOOKING"                # Quiero agendar consulta / reunión
    QUOTE_REQUEST = "QUOTE_REQUEST"    # Quiero presupuesto / cotización
    HUMAN_SUPPORT = "HUMAN_SUPPORT"    # Hablar con abogado / urgente / estoy detenido
    HOURS_QUERY = "HOURS_QUERY"        # ¿A qué hora atienden?
    LOCATION_QUERY = "LOCATION_QUERY"  # ¿Dónde está la oficina?
    
    # Nuevas intenciones para estudio jurídico
    CASE_INQUIRY = "CASE_INQUIRY"              # ¿Pueden ayudarme? / Tengo un caso de...
    SERVICE_INFO = "SERVICE_INFO"              # ¿Ven temas penales? / ¿Atienden VIF?
    PAYMENT_INFO = "PAYMENT_INFO"              # ¿Cómo son los pagos? / ¿Cuánto cobran?
    TIMEFRAME_QUERY = "TIMEFRAME_QUERY"        # ¿Cuánto demora? / ¿Cuánto tiempo tarda?
    LAWYER_IDENTITY = "LAWYER_IDENTITY"        # ¿Con quién hablo? / ¿Quién eres?
    BENEFIT_INFO = "BENEFIT_INFO"              # ¿Puedo salir en libertad condicional?
    PRIOR_RECORD_QUERY = "PRIOR_RECORD_QUERY"  # ¿Qué pasa con mis antecedentes?
    EXPULSION_INQUIRY = "EXPULSION_INQUIRY"    # Consultas sobre expulsión (administrativa o judicial)
    
    UNKNOWN = "UNKNOWN"                # No se pudo clasificar


class ExtractedIntent(BaseModel):
    """
    Resultado estructurado del clasificador IA.
    La IA solo extrae intención y entidades; no calcula ni responde.
    """
    intent: Intent
    
    # ══════════════════════════════════════════════════════════
    # CAMPOS LEGALES
    # ══════════════════════════════════════════════════════════
    
    # Área y asunto legal
    legal_area: Optional[str] = None            # "penal" | "familia" | "civil"
    legal_matter: Optional[str] = None          # "tráfico de drogas", "VIF", "custodia"
    
    # Contexto del caso
    description: Optional[str] = None           # Descripción breve del caso
    is_detained: Optional[bool] = None          # Si está detenido (CRÍTICO ⚠️)
    has_prior_record: Optional[bool] = None     # Si tiene antecedentes previos
    benefit_type: Optional[str] = None          # "libertad condicional", "salida alternativa"
    
    # Expulsión
    has_document: Optional[bool] = None         # Si tiene copia del documento de expulsión
    document_issuer: Optional[str] = None       # Quién emitió: "SERMIG", "PDI", "Tribunal"
    in_criminal_process: Optional[bool] = None  # Si está en proceso penal
    expulsion_type: Optional[str] = None        # "administrativa" | "judicial"
    
    # Urgencia
    urgency: Optional[str] = None               # "low" | "medium" | "high"
    
    # ══════════════════════════════════════════════════════════
    # CAMPOS GENERALES (mantener)
    # ══════════════════════════════════════════════════════════
    
    service: Optional[str] = None               # Servicio legal específico solicitado
    datetime_requested: Optional[str] = None    # Para BOOKING: "mañana 3pm"
    quote_description: Optional[str] = None     # Para QUOTE_REQUEST: descripción

    # ══════════════════════════════════════════════════════════
    # CAMPOS AUTOMOTRICES
    # ══════════════════════════════════════════════════════════
    secondary_intents: list[Intent] = Field(default_factory=list)
    brand: Optional[str] = None
    model: Optional[str] = None
    version: Optional[str] = None
    year: Optional[int] = None
    body_type: Optional[str] = None
    transmission: Optional[str] = None
    fuel_type: Optional[str] = None
    color: Optional[str] = None
    vehicle_price: Optional[int] = None
    max_budget: Optional[int] = None
    down_payment: Optional[int] = None
    max_monthly_payment: Optional[int] = None
    installments: Optional[int] = None
    financing_requested: Optional[bool] = None
    employment_type: Optional[str] = None
    credit_question: Optional[str] = None
    stock_requested: Optional[bool] = None
    branch_requested: Optional[str] = None
    trade_in_requested: Optional[bool] = None
    trade_in_brand: Optional[str] = None
    trade_in_model: Optional[str] = None
    trade_in_year: Optional[int] = None
    trade_in_mileage_km: Optional[int] = None
    media_type: Optional[str] = None
    media_subject: Optional[str] = None
