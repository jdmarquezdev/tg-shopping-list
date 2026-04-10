import os
import json
from typing import List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Configuración desde variables de entorno
# Por defecto apunta a shared/SHOPPING.md (el archivo real está en el workspace compartido)
SHOPPING_FILE_PATH = os.getenv("SHOPPING_FILE_PATH", "/data/shared/SHOPPING.md")
ALLOWED_USER_ID = os.getenv("ALLOWED_USER_ID", "5676298")
NOTIFICATION_FILE_PATH = os.getenv("NOTIFICATION_FILE_PATH", "/root/.openclaw/workspace/.shopping-changes.json")

# Log de configuración al arrancar (útil para debugging)
print(f"[CONFIG] SHOPPING_FILE_PATH: {SHOPPING_FILE_PATH}")
print(f"[CONFIG] ALLOWED_USER_ID: {ALLOWED_USER_ID}")
print(f"[CONFIG] NOTIFICATION_FILE_PATH: {NOTIFICATION_FILE_PATH}")
print(f"[CONFIG] File exists: {os.path.exists(SHOPPING_FILE_PATH)}")

app = FastAPI(title="Shopping List API")

# CORS habilitado
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir frontend estático
frontend_path = os.path.join(os.path.dirname(__file__), "frontend")
# Solo montar /assets si existe la carpeta (opcional)
assets_path = os.path.join(frontend_path, "assets")
if os.path.isdir(assets_path):
    app.mount("/assets", StaticFiles(directory=assets_path), name="assets")


@app.get("/")
def serve_frontend():
    """Sirve el frontend (index.html)"""
    return FileResponse(os.path.join(frontend_path, "index.html"))


class Item(BaseModel):
    name: str
    checked: bool = False


class Section(BaseModel):
    name: str
    items: List[Item] = []


class ItemAdd(BaseModel):
    name: str
    section: Optional[str] = "General"


class ItemToggle(BaseModel):
    name: str
    section: Optional[str] = "General"


class ItemComprado(BaseModel):
    section: str
    item: str
    action: str  # "checked" or "removed"


def normalize_section_name(name: str) -> str:
    """Normaliza el nombre de sección a MAYÚSCULAS"""
    return name.strip().upper()


def normalize_item_name(name: str) -> str:
    """
    Normaliza el nombre del producto:
    - Primera letra mayúscula
    - Resto minúsculas
    - Palabras como 'de', 'y', 'del', 'la', 'el' en minúscula (excepto primera palabra)
    """
    if not name:
        return name
    
    # Palabras que van en minúscula (excepto si son la primera)
    minor_words = {'de', 'y', 'del', 'la', 'el', 'los', 'las', 'un', 'una', 'unos', 'unas', 'con', 'sin', 'para', 'por'}
    
    words = name.strip().split()
    if not words:
        return name
    
    normalized_words = []
    for i, word in enumerate(words):
        if i == 0:
            # Primera palabra: primera letra mayúscula, resto minúsculas
            normalized_words.append(word.capitalize())
        elif word.lower() in minor_words:
            # Palabras menores en minúscula
            normalized_words.append(word.lower())
        else:
            # Otras palabras: primera letra mayúscula, resto minúsculas
            normalized_words.append(word.capitalize())
    
    return ' '.join(normalized_words)


def verify_user(x_telegram_user: Optional[str] = Header(None)):
    """Verifica que el usuario sea el permitido"""
    if not x_telegram_user:
        raise HTTPException(status_code=401, detail="Missing X-Telegram-User header")
    if x_telegram_user != ALLOWED_USER_ID:
        raise HTTPException(status_code=403, detail="Unauthorized user")
    return x_telegram_user


def read_shopping_list() -> List[Section]:
    """Lee la lista de la compra desde el archivo con secciones"""
    if not os.path.exists(SHOPPING_FILE_PATH):
        print(f"[WARNING] Archivo no encontrado: {SHOPPING_FILE_PATH}")
        print(f"[WARNING] Directorio /data existe: {os.path.exists('/data')}")
        if os.path.exists('/data'):
            try:
                print(f"[WARNING] Contenido de /data: {os.listdir('/data')}")
            except Exception as e:
                print(f"[WARNING] Error listando /data: {e}")
        return [Section(name="General", items=[])]
    
    sections = []
    current_section = None
    
    with open(SHOPPING_FILE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line_stripped = line.strip()
            
            # Saltar líneas vacías y título principal
            if not line_stripped or line_stripped == "# SHOPPING":
                continue
            
            # Detectar sección (## Nombre)
            if line_stripped.startswith("## "):
                section_name = line_stripped[3:].strip()
                # Normalizar sección a MAYÚSCULAS
                section_name = normalize_section_name(section_name)
                # Ignorar secciones que empiezan con "Fase" (documentación interna)
                if section_name.startswith("FASE"):
                    current_section = None  # No añadir esta sección
                    continue
                current_section = Section(name=section_name, items=[])
                sections.append(current_section)
                continue
            
            # Detectar item (- item o - [x] item)
            if line_stripped.startswith("- "):
                if current_section is None:
                    # Si no hay sección, crear "General"
                    current_section = Section(name="General", items=[])
                    sections.append(current_section)
                
                item_content = line_stripped[2:].strip()
                checked = item_content.startswith("[x]") or item_content.startswith("[X]")
                
                if checked:
                    name = item_content[3:].strip()
                else:
                    name = item_content
                
                # Normalizar el nombre del item al leer
                name = normalize_item_name(name)
                
                current_section.items.append(Item(name=name, checked=checked))
    
    # Filtrar secciones vacías (sin items o todos tachados)
    visible_sections = [
        section for section in sections
        if any(not item.checked for item in section.items)
    ]
    
    # Si no hay secciones visibles, devolver General vacía
    if not visible_sections:
        visible_sections = [Section(name="General", items=[])]
    
    return visible_sections


def write_shopping_list(sections: List[Section]):
    """Escribe la lista de la compra en el archivo con formato de secciones"""
    with open(SHOPPING_FILE_PATH, "w", encoding="utf-8") as f:
        f.write("# SHOPPING\n\n")
        
        for section in sections:
            f.write(f"## {section.name}\n")
            for item in section.items:
                if item.checked:
                    f.write(f"- [x] {item.name}\n")
                else:
                    f.write(f"- {item.name}\n")
            f.write("\n")


def find_section(sections: List[Section], name: str) -> Optional[Section]:
    """Busca una sección por nombre (case-insensitive)"""
    normalized_name = normalize_section_name(name)
    for section in sections:
        if section.name.upper() == normalized_name:
            return section
    return None


def write_notification(section: str, item: str, action: str):
    """Escribe una notificación en el archivo JSON para que Sancho pueda pollar"""
    notification = {
        "timestamp": datetime.utcnow().isoformat(),
        "section": section,
        "item": item,
        "action": action
    }
    
    # Leer notificaciones existentes o crear lista vacía
    notifications = []
    if os.path.exists(NOTIFICATION_FILE_PATH):
        try:
            with open(NOTIFICATION_FILE_PATH, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    notifications = json.loads(content)
        except (json.JSONDecodeError, IOError):
            notifications = []
    
    # Añadir nueva notificación
    notifications.append(notification)
    
    # Escribir de vuelta (mantener solo últimas 100 notificaciones)
    notifications = notifications[-100:]
    
    # Asegurar que el directorio existe
    os.makedirs(os.path.dirname(NOTIFICATION_FILE_PATH), exist_ok=True)
    
    with open(NOTIFICATION_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(notifications, f, indent=2, ensure_ascii=False)


@app.get("/api/lista")
def get_lista(user: str = Depends(verify_user)):
    """Obtiene la lista de la compra con secciones"""
    sections = read_shopping_list()
    return {"sections": sections}


@app.post("/api/agregar")
def agregar_item(item: ItemAdd, user: str = Depends(verify_user)):
    """Añade un nuevo item a la lista en la sección especificada"""
    sections = read_shopping_list()
    
    # Buscar o crear la sección (normalizar a MAYÚSCULAS)
    section_name = normalize_section_name(item.section) if item.section else "GENERAL"
    
    # Buscar sección sin importar el caso
    section = None
    for s in sections:
        if s.name.upper() == section_name:
            section = s
            break
    
    if not section:
        section = Section(name=section_name, items=[])
        sections.append(section)
    
    # Añadir el item (normalizar nombre del producto)
    normalized_name = normalize_item_name(item.name)
    section.items.append(Item(name=normalized_name, checked=False))
    write_shopping_list(sections)
    
    return {"message": "Item añadido", "sections": sections}


@app.post("/api/toggle")
def toggle_item(item: ItemToggle, user: str = Depends(verify_user)):
    """Marca/desmarca un item de la lista en la sección especificada"""
    sections = read_shopping_list()
    
    # Normalizar el nombre de la sección para la búsqueda
    section_name = normalize_section_name(item.section) if item.section else "GENERAL"
    section = find_section(sections, section_name)
    
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    
    # Normalizar el nombre del item para la búsqueda
    normalized_item_name = normalize_item_name(item.name)
    
    found = False
    for i in section.items:
        # Comparar con el nombre normalizado
        if i.name == normalized_item_name:
            i.checked = not i.checked
            found = True
            break
    
    if not found:
        raise HTTPException(status_code=404, detail="Item not found")
    
    write_shopping_list(sections)
    return {"message": "Item actualizado", "sections": sections}


@app.post("/api/comprado")
def item_comprado(data: ItemComprado, user: str = Depends(verify_user)):
    """
    Endpoint que recibe notificación cuando JD marca algo como comprado.
    Actualiza SHOPPING.md y escribe notificación para que Sancho pueda enterarse.
    """
    if data.action not in ["checked", "removed"]:
        raise HTTPException(status_code=400, detail="Action must be 'checked' or 'removed'")
    
    # Normalizar nombres
    normalized_section = normalize_section_name(data.section)
    normalized_item = normalize_item_name(data.item)
    
    sections = read_shopping_list()
    section = find_section(sections, normalized_section)
    
    if not section:
        # Si la sección no existe, crearla
        section = Section(name=normalized_section, items=[])
        sections.append(section)
    
    # Buscar o crear el item
    found = False
    for i in section.items:
        if i.name == normalized_item:
            if data.action == "checked":
                i.checked = True
            elif data.action == "removed":
                # Eliminar el item
                section.items.remove(i)
            found = True
            break
    
    if not found and data.action == "checked":
        # Si no existe y es "checked", añadirlo marcado
        section.items.append(Item(name=normalized_item, checked=True))
    
    write_shopping_list(sections)
    
    # Escribir notificación para Sancho (usando nombres normalizados)
    write_notification(normalized_section, normalized_item, data.action)
    
    return {
        "message": f"Item {data.action}: {data.item} en {data.section}",
        "notification_written": True
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
