# Configuración de la automotora demo

## 1. Preparar entorno

Usar Python 3.12 para las versiones fijadas en `requirements.txt`:

```powershell
python -m venv venv
.\venv\Scripts\activate
python -m pip install -r requirements.txt
```

Configurar PostgreSQL y las variables de `.env`.

## 2. Crear tablas y datos demo

```powershell
python seed_automotive.py
```

El proceso crea las tablas mediante el ciclo de inicio de la aplicación y luego
agrega una automotora demo con inventario, condiciones financieras y URLs de
demostración.

## 3. Probar el simulador

```powershell
python -m unittest test_automotive.py
```

Ejemplo:

```text
Precio:          $15.000.000
Pie:             $5.000.000
Plazo:           48 meses
Tasa referencial: 1%
Cuota estimada:  $263.338
```

## 4. Configurar datos reales

Después de la demo, sustituir mediante la API administrativa:

- `monthly_interest_rate`.
- `minimum_down_payment_pct`.
- `available_installments`.
- Requisitos de crédito.
- URL de agenda de prueba de manejo.
- URL de tasación.
- Inventario y precios.
- Imágenes, videos y fichas.

Las URLs de demo no deben utilizarse como material comercial real.

## 5. Memoria de financiamiento

La conversación activa se obtiene por negocio y teléfono del cliente. Los datos
financieros se guardan dentro de `Conversation.context.financing` y se combinan
con los datos ya existentes cuando llega una nueva modificación parcial.

Por ejemplo, si el primer mensaje contiene precio y pie, el siguiente puede
contener únicamente el plazo. El sistema reutiliza el precio y el pie anteriores,
actualiza el plazo y vuelve a calcular.
