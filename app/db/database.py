import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

# Asegurar que la URL use asyncpg
db_url = settings.database_url
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif not db_url.startswith("postgresql+asyncpg://"):
    raise ValueError(f"DATABASE_URL debe usar postgresql+asyncpg:// (actual: {db_url[:30]}...)")

logger = logging.getLogger(__name__)

engine = create_async_engine(
    db_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args={
        "timeout": 30,  # Timeout de conexión de 30 segundos
    }
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def _get_businesstype_enum_values(conn):
    result = await conn.scalars(text(
        "SELECT enumlabel FROM pg_enum "
        "JOIN pg_type ON pg_enum.enumtypid = pg_type.oid "
        "WHERE pg_type.typname = 'businesstype' "
        "ORDER BY enumsortorder"
    ))
    return result.all()


async def init_db():
    """Crea todas las tablas si no existen. Reintenta conexión si la DB está arrancando."""
    from app.db import models  # noqa: F401 – needed so Base sees all models
    
    max_retries = 5
    retry_delay = 2  # segundos
    
    for attempt in range(1, max_retries + 1):
        try:
            async with engine.begin() as conn:
                logger.info("Verificando enum 'businesstype' en la base de datos")
                exists = await conn.scalar(text(
                    "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'businesstype')"
                ))

                if exists:
                    values = await _get_businesstype_enum_values(conn)
                    for business_type in ("law_firm", "automotive"):
                        if business_type not in values:
                            logger.info("Agregando valor '%s' a enum 'businesstype'", business_type)
                            await conn.execute(text(
                                "DO $$ BEGIN "
                                "IF NOT EXISTS (SELECT 1 FROM pg_enum "
                                "JOIN pg_type ON pg_enum.enumtypid = pg_type.oid "
                                f"WHERE pg_type.typname = 'businesstype' AND enumlabel = '{business_type}') THEN "
                                f"ALTER TYPE businesstype ADD VALUE '{business_type}'; "
                                "END IF; "
                                "END $$;"
                            ))
                else:
                    logger.info("Tipo enum 'businesstype' no existe; será creado durante create_all")

                await conn.run_sync(Base.metadata.create_all)

                exists_after = await conn.scalar(text(
                    "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'businesstype')"
                ))
                if exists_after:
                    logger.info("Esquema automotriz verificado correctamente")
                else:
                    logger.warning("Después de create_all, el enum 'businesstype' sigue sin existir")
            
            # Si llegamos aquí, la conexión fue exitosa
            logger.info("Conexión a base de datos exitosa")
            return
            
        except Exception as exc:
            error_msg = str(exc).lower()
            if "starting up" in error_msg or "connection" in error_msg:
                if attempt < max_retries:
                    logger.warning(
                        f"Base de datos no disponible (intento {attempt}/{max_retries}). "
                        f"Reintentando en {retry_delay}s... Error: {exc}"
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 1.5  # Backoff exponencial
                else:
                    logger.error(
                        f"No se pudo conectar a la base de datos después de {max_retries} intentos. "
                        f"Error final: {exc}"
                    )
                    raise
            else:
                # Error no relacionado con la conexión, lanzar inmediatamente
                logger.error(f"Error inesperado al inicializar base de datos: {exc}")
                raise
