import os
import json
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
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


class Item(BaseModel):
    name: str
    checked: bool = False


class ItemAdd(BaseModel):
    name: str


def verify_user(x_telegram_user: Optional[str] = Header(None)):
    """Verifica que el usuario sea el permitido"""
    if not x_telegram_user:
        raise HTTPException(status_code=401, detail="Missing X-Telegram-User header")
    if x_telegram_user != ALLOWED_USER_ID:
        raise HTTPException(status_code=403, detail="Unauthorized user")
    return x_telegram_user


def read_shopping_list() -> List[Item]:
    """Lee la lista de la compra desde el archivo"""
    if not os.path.exists(SHOPPING_FILE_PATH):
        return []
    
    items = []
    with open(SHOPPING_FILE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            checked = line.startswith("[x]") or line.startswith("[X]")
            name = line[3:].strip() if checked else line.strip()
            items.append(Item(name=name, checked=checked))
    return items


def write_shopping_list(items: List[Item]):
    """Escribe la lista de la compra en el archivo"""
    with open(SHOPPING_FILE_PATH, "w", encoding="utf-8") as f:
        f.write("# Lista de la compra\n\n")
        for item in items:
            if item.checked:
                f.write(f"[x] {item.name}\n")
            else:
                f.write(f"[ ] {item.name}\n")


@app.get("/api/lista")
def get_lista(user: str = Depends(verify_user)):
    """Obtiene la lista de la compra"""
    items = read_shopping_list()
    return {"items": items}


@app.post("/api/agregar")
def agregar_item(item: ItemAdd, user: str = Depends(verify_user)):
    """Añade un nuevo item a la lista"""
    items = read_shopping_list()
    items.append(Item(name=item.name, checked=False))
    write_shopping_list(items)
    return {"message": "Item añadido", "items": items}


@app.post("/api/toggle")
def toggle_item(item: ItemAdd, user: str = Depends(verify_user)):
    """Marca/desmarca un item de la lista"""
    items = read_shopping_list()
    found = False
    for i in items:
        if i.name == item.name:
            i.checked = not i.checked
            found = True
            break
    
    if not found:
        raise HTTPException(status_code=404, detail="Item not found")
    
    write_shopping_list(items)
    return {"message": "Item actualizado", "items": items}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
