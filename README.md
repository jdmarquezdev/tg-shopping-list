# 🛒 Shopping Mini App

Telegram Mini App para gestionar tu lista de la compra.

## Características

- ✅ Añadir productos a la lista
- ✅ Marcar/desmarcar productos como comprados
- ✅ Tema nativo de Telegram (claro/oscuro automático)
- ✅ Feedback háptico en móvil
- ✅ Autenticación por usuario de Telegram

## Estructura

```
tg-shopping-list/
├── frontend/
│   └── index.html          # Interfaz web mobile-first
├── backend/
│   ├── main.py             # API FastAPI
│   ├── requirements.txt    # Dependencias Python
│   └── Dockerfile          # Contenedor backend
├── docker-compose.yml      # Desarrollo local
├── README.md               # Este archivo
└── .gitignore
```

## Despliegue

### Variables de entorno

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `SHOPPING_FILE_PATH` | Ruta al archivo de la lista | `/data/SHOPPING.md` |
| `ALLOWED_USER_ID` | ID de usuario permitido | `123456789` |

### Con Docker Compose

```bash
docker-compose up --build
```

### En un servidor (Coolify, Railway, etc.)

1. Conecta tu repositorio de GitHub
2. Configura las variables de entorno
3. Añade un volumen persistente para `/data` (si usas Docker)
4. Despliega

## Configuración en BotFather

1. Abre [@BotFather](https://t.me/BotFather) en Telegram
2. `/newapp` - crear nueva Mini App
3. Selecciona tu bot
4. Introduce:
   - **Nombre:** Lista de la Compra
   - **Descripción:** Gestiona tu lista de la compra
   - **Foto:** (opcional)
   - **Web App URL:** `https://tu-dominio.com/frontend/`
   - **Short name:** `shopping`

5. BotFather te dará un enlace tipo: `https://t.me/tu_bot/shopping`

## Desarrollo local

```bash
# Backend
cd backend
pip install -r requirements.txt
SHOPPING_FILE_PATH=./SHOPPING.md uvicorn main:app --reload
```

El frontend se sirve directamente desde Telegram, pero puedes abrir `frontend/index.html` en un navegador para desarrollo.

## API Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/lista` | Obtiene la lista completa |
| POST | `/api/agregar` | Añade un producto |
| POST | `/api/toggle` | Marca/desmarca producto |

### Headers requeridos

```
X-Telegram-User: <user_id>
```

### Ejemplos

```bash
# Obtener lista
curl -H "X-Telegram-User: 123456789" https://tu-dominio.com/api/lista

# Añadir item
curl -X POST -H "X-Telegram-User: 123456789" \
  -H "Content-Type: application/json" \
  -d '{"name": "Leche"}' \
  https://tu-dominio.com/api/agregar

# Toggle item
curl -X POST -H "X-Telegram-User: 123456789" \
  -H "Content-Type: application/json" \
  -d '{"name": "Leche"}' \
  https://tu-dominio.com/api/toggle
```

## Notas

- El archivo `SHOPPING.md` se crea automáticamente en la primera escritura
- Formato del archivo: `[x] producto` (comprado) o `[ ] producto` (pendiente)
- Solo el usuario configurado en `ALLOWED_USER_ID` puede modificar la lista
