-- Migration: Agregar índice único a wa_message_id para prevenir mensajes duplicados
-- Fecha: 2026-07-24
-- Descripción: Agrega un índice único y constraint a wa_message_id en la tabla messages
--              para prevenir que se procesen mensajes duplicados de WhatsApp

-- Paso 1: Eliminar mensajes duplicados existentes (mantener el más antiguo)
WITH duplicates AS (
    SELECT 
        id,
        wa_message_id,
        ROW_NUMBER() OVER (PARTITION BY wa_message_id ORDER BY created_at ASC) AS rn
    FROM messages
    WHERE wa_message_id IS NOT NULL
)
DELETE FROM messages
WHERE id IN (
    SELECT id FROM duplicates WHERE rn > 1
);

-- Paso 2: Crear índice único en wa_message_id (permitiendo NULLs)
CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_wa_message_id_unique 
ON messages (wa_message_id)
WHERE wa_message_id IS NOT NULL;

-- Paso 3: Agregar constraint de unicidad
ALTER TABLE messages 
DROP CONSTRAINT IF EXISTS messages_wa_message_id_key;

-- Nota: El índice parcial (WHERE wa_message_id IS NOT NULL) permite múltiples filas con NULL
-- pero garantiza unicidad para valores no-NULL

-- Verificación
SELECT 
    COUNT(*) as total_messages,
    COUNT(DISTINCT wa_message_id) as unique_wa_ids,
    COUNT(*) - COUNT(DISTINCT wa_message_id) as potential_duplicates
FROM messages
WHERE wa_message_id IS NOT NULL;

-- Output esperado: potential_duplicates debe ser 0
