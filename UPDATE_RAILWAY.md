# 🚨 ACTUALIZAR RAILWAY - URGENTE

## Problema Detectado
Railway está usando una URL de túnel antigua que **no tiene los modelos necesarios**:
- ❌ URL antigua: `https://len-san-kings-relying.trycloudflare.com/v1`
- ❌ Solo tiene modelo de texto (llama3.2:3b)
- ❌ Falta modelo de visión (llava:7b)

## Solución

### 1. Verifica la URL actual del túnel
El túnel que está corriendo ahora tiene esta URL (cópiala de la terminal donde corre `cloudflared`).

### 2. Actualiza en Railway
Ve a tu proyecto en Railway y actualiza la variable de entorno:

```
OLLAMA_BASE_URL=https://[TU-URL-DEL-TUNEL].trycloudflare.com/v1
```

**Ejemplo (NO uses esta, usa la tuya):**
```
OLLAMA_BASE_URL=https://len-san-kings-relying.trycloudflare.com/v1
```

### 3. Guarda y Redespliega
- Haz clic en "Save"
- Railway redespliegará automáticamente

### 4. Prueba
Envía "Hola" al bot de WhatsApp y debería responder correctamente.

---

## ✅ Verificación de Modelos

Tu túnel local tiene ambos modelos necesarios:
- ✅ llama3.2:3b (clasificación de intenciones)
- ✅ llava:7b (análisis de imágenes)

Puedes verificarlo con:
```powershell
curl http://localhost:8081/v1/models -Method GET
```

---

## 🔄 Mantener el Túnel Activo

**IMPORTANTE:** El túnel debe estar corriendo 24/7 para que el bot funcione.

- ✅ Deja la ventana de PowerShell abierta con `cloudflared`
- ❌ Si cierras la ventana, el bot dejará de funcionar
- ⚠️ La URL del túnel puede cambiar si lo reinicias

---

## 📝 Comandos Útiles

### Ver logs de Railway en tiempo real:
```bash
# Instala Railway CLI si no lo tienes
npm install -g @railway/cli

# Login
railway login

# Ver logs
railway logs
```

### Verificar que el túnel funciona:
```powershell
curl https://[TU-URL].trycloudflare.com/v1/models
```

Debería devolver JSON con dos modelos:
```json
{
  "object": "list",
  "data": [
    {"id": "llama3.2:3b", ...},
    {"id": "llava:7b", ...}
  ]
}
```
