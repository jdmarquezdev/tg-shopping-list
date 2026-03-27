import os
import json
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Configuración desde variables de entorno
SHOPPING_FILE_PATH = os.getenv("SHOPPING_FILE_PATH", "SHOPPING.md")
ALLOWED_USER_ID = os.getenv("ALLOWED_USER_ID", "5676298")

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
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/assets", StaticFiles(directory=os.path.join(frontend_path, "assets")), name="assets")


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
                
                current_section.items.append(Item(name=name, checked=checked))
    
    # Si no hay secciones, devolver General vacía
    if not sections:
        sections = [Section(name="General", items=[])]
    
    return sections


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
    """Busca una sección por nombre"""
    for section in sections:
        if section.name == name:
            return section
    return None


@app.get("/api/lista")
def get_lista(user: str = Depends(verify_user)):
    """Obtiene la lista de la compra con secciones"""
    sections = read_shopping_list()
    return {"sections": sections}


@app.post("/api/agregar")
def agregar_item(item: ItemAdd, user: str = Depends(verify_user)):
    """Añade un nuevo item a la lista en la sección especificada"""
    sections = read_shopping_list()
    
    # Buscar o crear la sección
    section_name = item.section if item.section else "General"
    section = find_section(sections, section_name)
    
    if not section:
        section = Section(name=section_name, items=[])
        sections.append(section)
    
    # Añadir el item
    section.items.append(Item(name=item.name, checked=False))
    write_shopping_list(sections)
    
    return {"message": "Item añadido", "sections": sections}


@app.post("/api/toggle")
def toggle_item(item: ItemToggle, user: str = Depends(verify_user)):
    """Marca/desmarca un item de la lista en la sección especificada"""
    sections = read_shopping_list()
    
    section_name = item.section if item.section else "General"
    section = find_section(sections, section_name)
    
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    
    found = False
    for i in section.items:
        if i.name == item.name:
            i.checked = not i.checked
            found = True
            break
    
    if not found:
        raise HTTPException(status_code=404, detail="Item not found")
    
    write_shopping_list(sections)
    return {"message": "Item actualizado", "sections": sections}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
