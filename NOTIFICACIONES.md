# Notificaciones Automáticas - JD → Sancho

## Resumen

Cuando JD marque un item como comprado en la Mini App de Telegram, Sancho recibirá la notificación automáticamente y podrá actualizar la lista/memoria.

## Implementación

### 1. Backend Endpoint (`POST /api/comprado`)

El backend ahora tiene un nuevo endpoint que recibe:

```json
{
  "section": "Frutas",
  "item": "Manzanas",
  "action": "checked"  // o "removed"
}
```

**Qué hace:**
- Actualiza `SHOPPING.md` (marca/desmarca o elimina el item)
- Escribe una notificación en `/root/.openclaw/workspace/.shopping-changes.json`

### 2. Archivo de Notificaciones

**Ubicación:** `/root/.openclaw/workspace/.shopping-changes.json`

**Formato:**
```json
[
  {
    "timestamp": "2026-03-27T20:45:00.000000",
    "section": "Frutas",
    "item": "Manzanas",
    "action": "checked"
  },
  {
    "timestamp": "2026-03-27T20:46:00.000000",
    "section": "Lácteos",
    "item": "Leche",
    "action": "checked"
  }
]
```

**Características:**
- Se mantiene un máximo de 100 notificaciones (las más recientes)
- Formato JSON fácil de parsear
- Incluye timestamp para ordenar y deduplicar

### 3. Cómo Sancho Recibe las Notificaciones

**Opción A: Polling en Heartbeat (Recomendado)**

Sancho debe leer el archivo de notificaciones durante sus heartbeats (cada ~30 minutos o cuando se active):

```python
# Pseudocódigo para Sancho
import json
import os

NOTIFICATION_FILE = "/root/.openclaw/workspace/.shopping-changes.json"
STATE_FILE = "/root/.openclaw/workspace/.shopping-last-processed.json"

def check_shopping_changes():
    if not os.path.exists(NOTIFICATION_FILE):
        return []
    
    # Leer último timestamp procesado
    last_processed = ""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            state = json.load(f)
            last_processed = state.get("last_timestamp", "")
    
    # Leer nuevas notificaciones
    with open(NOTIFICATION_FILE) as f:
        notifications = json.load(f)
    
    nuevas = [n for n in notifications if n["timestamp"] > last_processed]
    
    if nuevas:
        # Actualizar estado
        with open(STATE_FILE, "w") as f:
            json.dump({"last_timestamp": nuevas[-1]["timestamp"]}, f)
        
        # Procesar cada notificación
        for n in nuevas:
            mensaje = f"JD marcó como {n['action']}: {n['item']} de {n['section']}"
            # Enviar a memoria o actualizar lista
    
    return nuevas
```

**Opción B: Polling cada 30 segundos**

Si se necesita mayor inmediatez, Sancho puede hacer polling del archivo cada 30 segundos durante la sesión activa.

## Deploy en Coolify

### Pasos:

1. **Subir cambios al repo:**
   ```bash
   cd /root/.openclaw/workspace-rucio/projects/tg-shopping-list
   git add backend/main.py
   git commit -m "Add /api/comprado endpoint for JD notifications"
   git push
   ```

2. **En Coolify:**
   - Ir al proyecto `tg-shopping-list`
   - El deploy automático debería activarse con el push
   - Si no, hacer deploy manual desde el dashboard

3. **Variables de entorno (si cambian):**
   ```bash
   SHOPPING_FILE_PATH=/root/.openclaw/workspace-rucio/projects/tg-shopping-list/SHOPPING.md
   ALLOWED_USER_ID=5676298
   NOTIFICATION_FILE_PATH=/root/.openclaw/workspace/.shopping-changes.json
   ```

4. **Permisos del archivo de notificaciones:**
   ```bash
   # Asegurar que el directorio existe y es escribible
   mkdir -p /root/.openclaw/workspace
   chmod 755 /root/.openclaw/workspace
   ```

## Testing

**Probar el endpoint:**

```bash
curl -X POST http://localhost:8000/api/comprado \
  -H "Content-Type: application/json" \
  -H "X-Telegram-User: 5676298" \
  -d '{"section": "Test", "item": "Item de prueba", "action": "checked"}'
```

**Verificar archivo de notificaciones:**

```bash
cat /root/.openclaw/workspace/.shopping-changes.json
```

## Mini App Integration

En la Mini App de Telegram, cuando JD marque un item:

```javascript
// Cuando se hace check/uncheck
async function onItemToggle(section, item, checked) {
  const action = checked ? "checked" : "removed";
  
  await fetch('/api/comprado', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Telegram-User': telegramUserId
    },
    body: JSON.stringify({ section, item, action })
  });
}
```

## Resumen del Flujo

```
JD (Mini App) 
    ↓ POST /api/comprado
Backend FastAPI
    ↓ 1. Actualiza SHOPPING.md
    ↓ 2. Escribe en .shopping-changes.json
    ↓
Sancho (polling heartbeat)
    ↓ Lee archivo
    ↓ Procesa notificaciones nuevas
    ↓ Actualiza memoria/lista
```
