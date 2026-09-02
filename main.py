import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

import models
from database import SessionLocal, engine, get_db

# ============ UTILITÁRIOS DE SENHA (PBKDF2 - sem dep externa) ============

_PBKDF2_ITER = 260_000


def hash_senha(senha: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(salt), _PBKDF2_ITER)
    return f"pbkdf2_sha256${_PBKDF2_ITER}${salt}${h.hex()}"


def verificar_senha(senha: str, armazenada: str) -> bool:
    try:
        _, iteracoes, salt, esperado = armazenada.split("$")
        h = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(salt), int(iteracoes))
        return hmac.compare_digest(h.hex(), esperado)
    except Exception:
        return False


# ============ JWT ============

SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
JWT_ALG = "HS256"
JWT_EXP_DIAS = 14


def criar_token(user_id: int) -> str:
    agora = datetime.utcnow()
    payload = {
        "sub": str(user_id),
        "iat": agora,
        "exp": agora + timedelta(days=JWT_EXP_DIAS),
        "jti": secrets.token_hex(8),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALG)


def _extrair_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    # fallback: também aceita token no query string (bom p/ compatibilidade)
    token = request.query_params.get("token")
    if token:
        return token
    raise HTTPException(status_code=401, detail="Autenticação necessária")


def get_usuario_atual(request: Request, db: Session = Depends(get_db)) -> models.User:
    token = _extrair_token(request)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALG])
        user_id = int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Sessão expirada ou inválida. Faça login novamente.")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or not user.ativo:
        raise HTTPException(status_code=401, detail="Usuário não encontrado ou inativo.")
    return user


def require_admin(is_master: bool = False):
    def dependente(usuario: models.User = Depends(get_usuario_atual)):
        if is_master and usuario.role != "adminMaster":
            raise HTTPException(status_code=403, detail="Acesso restrito ao admin master.")
        if not is_master and usuario.role not in ("admin", "adminMaster"):
            raise HTTPException(status_code=403, detail="Permissão negada.")
        return usuario

    return dependente


# ============ RATE LIMIT (anti-spam / força bruta) ============

_MINUTO_RATELIMIT = 10  # tentativas por janela
_JANELA_RATELIMIT = 60  # segundos
_tentativas: dict = {}  # ip -> [timestamps]


def rate_limit(request: Request):
    ip = request.client.host if request.client else "unknown"
    agora = time.time()
    hist = [t for t in _tentativas.get(ip, []) if agora - t < _JANELA_RATELIMIT]
    if len(hist) >= _MINUTO_RATELIMIT:
        raise HTTPException(status_code=429, detail="Muitas tentativas. Aguarde um minuto.")
    hist.append(agora)
    _tentativas[ip] = hist


# ============ APP ============

app = FastAPI(title="Omnisys Pro API", docs_url=None, redoc_url=None, openapi_url=None)


class SegurancaMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def enviar(mensagem):
            if mensagem["type"] == "http.response.start":
                headers = list(mensagem.get("headers", []))
                extra = {
                    b"x-content-type-options": b"nosniff",
                    b"x-frame-options": b"DENY",
                    b"referrer-policy": b"no-referrer",
                    b"x-xss-protection": b"1; mode=block",
                    b"cache-control": b"no-store",
                }
                presentes = {k.lower() for k, _ in headers}
                for k, v in extra.items():
                    if k not in presentes:
                        headers.append((k, v))
                mensagem["headers"] = headers
            await send(mensagem)

        await self.app(scope, receive, enviar)


app.add_middleware(SegurancaMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

models.Base.metadata.create_all(bind=engine)


# ============ FORMULÁRIOS (Pydantic) ============

class UsuarioCreate(BaseModel):
    nome: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    ramo: str = Field("geral", max_length=40)
    doc: str = Field("", max_length=40)
    tel: str = Field("", max_length=40)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class SyncBody(BaseModel):
    data: dict


def _json_user(u: models.User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "nome": u.nome,
        "ramo": u.ramo,
        "doc": u.doc,
        "tel": u.tel,
        "role": u.role,
        "plan_type": u.plan_type,
        "has_sac": u.has_sac,
        "has_suggestions": u.has_suggestions,
        "has_evaluations": u.has_evaluations,
    }


# ============ ROTAS PÚBLICAS ============

@app.get("/", response_class=HTMLResponse)
def home():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h3>Arquivo index.html não encontrado na pasta do projeto!</h3>"


@app.post("/api/usuarios/", dependencies=[Depends(rate_limit)])
def criar_usuario(dados: UsuarioCreate, db: Session = Depends(get_db)):
    email = dados.email.lower().strip()
    existente = db.query(models.User).filter(models.User.email == email).first()
    if existente:
        raise HTTPException(status_code=400, detail="Este e-mail já está cadastrado.")

    novo = models.User(
        email=email,
        hashed_password=hash_senha(dados.password),
        nome=dados.nome.strip(),
        ramo=dados.ramo.strip() or "geral",
        doc=dados.doc.strip(),
        tel=dados.tel.strip(),
        role="admin",
        plan_type="basico",
        has_sac=True,
        has_suggestions=True,
        has_evaluations=True,
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return {"message": "Conta criada com sucesso", "id": novo.id}


@app.post("/api/login", dependencies=[Depends(rate_limit)])
def fazer_login(dados: LoginRequest, db: Session = Depends(get_db)):
    email = dados.email.lower().strip()
    usuario = db.query(models.User).filter(models.User.email == email).first()
    if not usuario or not verificar_senha(dados.password, usuario.hashed_password):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")
    if not usuario.ativo:
        raise HTTPException(status_code=403, detail="Conta desativada.")

    return {"token": criar_token(usuario.id), "user": _json_user(usuario)}


@app.get("/api/me")
def me(usuario: models.User = Depends(get_usuario_atual)):
    return _json_user(usuario)


# ============ SYNC (espelho do localStorage) ============

@app.get("/api/sync")
def sync_get(usuario: models.User = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    linha = db.query(models.SyncData).filter(models.SyncData.user_id == usuario.id).first()
    if not linha:
        return {"data": {}}
    try:
        dados = json.loads(linha.data)
    except Exception:
        dados = {}
    return {"data": dados}


@app.put("/api/sync")
@app.post("/api/sync")
def sync_put(body: SyncBody, usuario: models.User = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    if len(json.dumps(body.data)) > 3_000_000:
        raise HTTPException(status_code=413, detail="Dados grandes demais (máx. ~3MB).")

    linha = db.query(models.SyncData).filter(models.SyncData.user_id == usuario.id).first()
    if linha:
        linha.data = json.dumps(body.data)
    else:
        linha = models.SyncData(user_id=usuario.id, data=json.dumps(body.data))
        db.add(linha)
    db.commit()
    return {"message": "Sincronizado"}


# ============ ADMIN MASTER (flag guard) ============

@app.get("/api/trocar-senha")
def trocar_senha(senha: str, usuario: models.User = Depends(require_admin(is_master=True)), db: Session = Depends(get_db)):
    usuario.hashed_password = hash_senha(senha)
    db.commit()
    return {"message": "Senha alterada com sucesso"}


# ============ MASTER DO AMBIENTE ============

def _garantir_master():
    email = os.getenv("MASTER_EMAIL", "").lower().strip()
    senha = os.getenv("MASTER_PASSWORD", "")
    if not email or not senha:
        return
    db = SessionLocal()
    try:
        master = db.query(models.User).filter(models.User.email == email).first()
        if master:
            master.role = "adminMaster"
            master.ativo = True
            if senha.startswith("pbkdf2_sha256$"):
                master.hashed_password = senha
            else:
                master.hashed_password = hash_senha(senha)
        else:
            db.add(
                models.User(
                    email=email,
                    hashed_password=hash_senha(senha),
                    nome="Admin Master",
                    ramo="geral",
                    role="adminMaster",
                    plan_type="completo",
                    has_sac=True,
                    has_suggestions=True,
                    has_evaluations=True,
                )
            )
        db.commit()
    finally:
        db.close()


_garantir_master()