import os
import random
from datetime import datetime, timezone

import socketio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import Column, Integer, String, DateTime, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ---------------------------------------------------------------------------
# Banco de dados
# ---------------------------------------------------------------------------
# Em produção no Render, defina a variável de ambiente DATABASE_URL apontando
# para um banco Postgres (gratuito) para que o histórico não se perca quando
# o serviço "dorme". Sem essa variável, usamos um arquivo SQLite local --
# funciona, mas o Render apaga o arquivo sempre que o serviço reinicia após
# ficar inativo.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./campanha.db")
if DATABASE_URL.startswith("postgres://"):
    # Render fornece a URL no formato antigo; SQLAlchemy exige "postgresql://"
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Entry(Base):
    __tablename__ = "entries"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False)       # "narracao" | "acao" | "rolagem"
    author = Column(String, nullable=False)
    text = Column(String, nullable=True)
    roll = Column(Integer, nullable=True)
    ts = Column(DateTime, default=lambda: datetime.now(timezone.utc))


Base.metadata.create_all(bind=engine)


def entry_to_dict(e: Entry) -> dict:
    return {
        "id": e.id,
        "type": e.type,
        "author": e.author,
        "text": e.text,
        "roll": e.roll,
        "ts": e.ts.replace(tzinfo=timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# FastAPI + Socket.IO
# ---------------------------------------------------------------------------
fastapi_app = FastAPI(title="Diário da Campanha")
templates = Jinja2Templates(directory="templates")

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)


@fastapi_app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@fastapi_app.get("/healthz")
async def healthz():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Eventos Socket.IO
# ---------------------------------------------------------------------------
@sio.event
async def connect(sid, environ):
    pass


@sio.event
async def disconnect(sid):
    pass


@sio.event
async def join(sid, data):
    """Um jogador ou mestre entra na mesa."""
    name = (data.get("name") or "Aventureiro").strip()[:30]
    role = data.get("role") if data.get("role") in ("mestre", "jogador") else "jogador"
    await sio.save_session(sid, {"name": name, "role": role})

    db = SessionLocal()
    try:
        entries = db.query(Entry).order_by(Entry.id.asc()).limit(300).all()
        history = [entry_to_dict(e) for e in entries]
    finally:
        db.close()

    await sio.emit("history", history, to=sid)


@sio.event
async def send_message(sid, data):
    """Mestre narra ou jogador registra uma ação -- texto livre em ambos os casos."""
    session = await sio.get_session(sid)
    name = session["name"]
    role = session["role"]
    text = (data.get("text") or "").strip()
    if not text:
        return

    entry_type = "narracao" if role == "mestre" else "acao"

    db = SessionLocal()
    try:
        entry = Entry(type=entry_type, author=name, text=text)
        db.add(entry)
        db.commit()
        db.refresh(entry)
        payload = entry_to_dict(entry)
    finally:
        db.close()

    await sio.emit("new_entry", payload)


@sio.event
async def roll_dice(sid, data):
    """Rola um d20. O resultado é só o número -- a interpretação fica com o mestre."""
    session = await sio.get_session(sid)
    name = session["name"]
    roll = random.randint(1, 20)

    db = SessionLocal()
    try:
        entry = Entry(type="rolagem", author=name, roll=roll)
        db.add(entry)
        db.commit()
        db.refresh(entry)
        payload = entry_to_dict(entry)
    finally:
        db.close()

    await sio.emit("new_entry", payload)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)
