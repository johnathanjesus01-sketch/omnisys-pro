import os
from typing import Optional

from typing import Optional
from pydantic import BaseModel,Field
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import models
from database import SessionLocal, engine, get_db

app = FastAPI()

# Modelo Pydantic para receber o cadastro de utilizadores
class UsuarioCreate(BaseModel):
    nome: str
    email: str
    password: str
    role: str = "usuario"

models.Base.metadata.create_all(bind=engine)

app.mount("/static", StaticFiles(directory="."), name="static")
templates = Jinja2Templates(directory=".")


@app.post("/api/usuarios/")
def criar_usuario(dados: UsuarioCreate, db: Session = Depends(get_db)):
    usuario_existente = db.query(models.User).filter(models.User.email == dados.email).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="Este e-mail já está cadastrado.")

    novo_usuario = models.User(
        email=dados.email,
        hashed_password=dados.password,
        role=dados.role,
        plan_type="basic",
        has_sac=True,
        has_suggestions=True,
        has_evaluations=True
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    return {"message": "Utilizador criado com sucesso", "id": novo_usuario.id}

# Importações do seu banco de dados
import models
from database import SessionLocal, engine

# Função para gerenciar a conexão com o banco de dados
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
@app.get("/setup-master")
def setup_master(db: Session = Depends(get_db)):
    # Verifica se o master já existe para não duplicar
    master_existente = db.query(models.User).filter(models.User.email == "master@omnisys.com").first()

    if not master_existente:
        novo_master = models.User(
            email="master@omnisys.com",
            hashed_password="senha_master_123",  # Depois você troca no sistema
            role="adminMaster",
            plan_type="completo",
            has_sac=True,
            has_suggestions=True,
            has_evaluations=True
        )
        db.add(novo_master)
        db.commit()
        return {"mensagem": "Usuário Admin Master criado com SUCESSO!"}

    return {"mensagem": "O Admin Master já existe no banco!"}
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

def get_db():

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ROTA RAIZ PARA ENTREGAR O FRONT-END EM PORTUGUÊS ---
@app.get("/", response_class=HTMLResponse, tags=["Geral"])
def home():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h3>Arquivo index.html não encontrado na pasta do projeto!</h3>"

# --- SCHEMAS (Pydantic) ---
class EmpresaCreate(BaseModel):
    nome_fantasia: str = Field(..., description="Nome fantasia da empresa ou cliente")
    cnpj: str = Field(..., description="CNPJ cadastrado")
    ramo: Optional[str] = Field("geral", description="Ramo de atuação (ex: odonto, oficina, loja)")

class EstoqueCreate(BaseModel):
    empresa_id: int = Field(..., description="ID da empresa dona do estoque")
    nome: str = Field(..., description="Nome do produto ou peça")
    quantidade: int = Field(..., description="Quantidade em estoque")
    preco_unitario: float = Field(..., description="Preço de venda unitário")

class AtividadeCreate(BaseModel):
    empresa_id: int = Field(..., description="ID da empresa")
    titulo: str = Field(..., description="Título da atividade")
    descricao: Optional[str] = Field(None, description="Detalhes da tarefa")
    status: Optional[str] = Field("a_fazer", description="a_fazer ou concluida")

class FaturamentoCreate(BaseModel):
    empresa_id: int = Field(..., description="ID da empresa")
    descricao: str = Field(..., description="Descrição da transação")
    valor: float = Field(..., description="Valor em dinheiro")
    tipo: str = Field(..., description="receita ou despesa")

# --- ROTAS DA API ---

@app.post("/empresas/", summary="Cadastrar Nova Empresa", tags=["Empresas"])
def criar_empresa(empresa: EmpresaCreate, db: Session = Depends(get_db)):
    db_empresa = models.Empresa(nome_fantasia=empresa.nome_fantasia, cnpj=empresa.cnpj, ramo=empresa.ramo)
    db.add(db_empresa)
    db.commit()
    db.refresh(db_empresa)
    return db_empresa

@app.get("/empresas/", summary="Listar Todas as Empresas", tags=["Empresas"])
def listar_empresas(db: Session = Depends(get_db)):
    return db.query(models.Empresa).all()

@app.post("/estoque/", summary="Adicionar Produto ao Estoque", tags=["Estoque"])
def adicionar_estoque(item: EstoqueCreate, db: Session = Depends(get_db)):
    novo_item = models.ProdutoEstoque(**item.dict())
    db.add(novo_item)
    db.commit()
    db.refresh(novo_item)
    return novo_item

@app.get("/estoque/{empresa_id}", summary="Listar Estoque por Empresa", tags=["Estoque"])
def listar_estoque(empresa_id: int, db: Session = Depends(get_db)):
    return db.query(models.ProdutoEstoque).filter(models.ProdutoEstoque.empresa_id == empresa_id).all()
# Rota para cadastrar um novo produto no estoque
@app.post("/api/estoque/", summary="Cadastrar Produto no Estoque", tags=["Estoque"])
def cadastrar_produto_estoque(item: EstoqueCreate, db: Session = Depends(get_db)):
    novo_produto = models.ProdutoEstoque(**item.model_dump())
    db.add(novo_produto)
    db.commit()
    db.refresh(novo_produto)
    return novo_produto

# Rota para excluir um ou mais produtos do estoque pelo ID
@app.delete("/api/estoque/deletar", summary="Excluir Produtos do Estoque", tags=["Estoque"])
def excluir_produtos_estoque(ids: list[int], db: Session = Depends(get_db)):
    db.query(models.ProdutoEstoque).filter(models.ProdutoEstoque.id.in_(ids)).delete(synchronize_session=False)
    db.commit()
    return {"message": "Produtos excluídos com sucesso"}
@app.post("/atividades/", summary="Criar Nova Atividade", tags=["Atividades"])
def criar_atividade(atv: AtividadeCreate, db: Session = Depends(get_db)):
    nova_atv = models.Atividade(**atv.dict())
    db.add(nova_atv)
    db.commit()
    db.refresh(nova_atv)
    return nova_atv

@app.get("/atividades/{empresa_id}", summary="Listar Atividades por Empresa", tags=["Atividades"])
def listar_atividades(empresa_id: int, db: Session = Depends(get_db)):
    return db.query(models.Atividade).filter(models.Atividade.empresa_id == empresa_id).all()

@app.post("/faturamento/", summary="Registrar Transação Financeira", tags=["Faturamento"])
def registrar_faturamento(fat: FaturamentoCreate, db: Session = Depends(get_db)):
    transacao = models.TransacaoFinanceira(**fat.dict())
    db.add(transacao)
    db.commit()
    db.refresh(transacao)
    return transacao

@app.get("/faturamento/{empresa_id}", summary="Relatório de Faturamento por Empresa", tags=["Faturamento"])
def relatorio_faturamento(empresa_id: int, db: Session = Depends(get_db)):
    return db.query(models.TransacaoFinanceira).filter(models.TransacaoFinanceira.empresa_id == empresa_id).all()


from fastapi import Depends, HTTPException, status


# (Outros imports necessários...)

@app.post("/api/admin/criar-usuario")
async def criar_usuario_master(email: str, password: str, role: str, plan_type: str, has_sac: bool,
                               has_suggestions: bool, has_evaluations: bool, db: Session = Depends(get_db)):
    # Aqui você valida se quem está chamando é o Admin Master

    novo_usuario = models.User(
        email=email,
        hashed_password=password,  # Idealmente com hash
        role=role,
        plan_type=plan_type,
        has_sac=has_sac,
        has_suggestions=has_suggestions,
        has_evaluations=has_evaluations)
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    return {"message": "Usuário criado com sucesso com os níveis de acesso definidos!"}


# Esquema para receber os dados do login do frontend
class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/api/login")
def fazer_login(dados: LoginRequest, db: Session = Depends(get_db)):
    # Procura o usuário no banco pelo email
    usuario = db.query(models.User).filter(models.User.email == dados.email).first()

    # Verifica se achou e se a senha bate (para o MVP estamos comparando direto)
    if not usuario or usuario.hashed_password != dados.password:
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    # Se deu certo, devolve os dados e permissões do usuário
    return {
        "id": usuario.id,
        "email": usuario.email,
        "role": usuario.role,
        "plan_type": usuario.plan_type,
        "has_sac": usuario.has_sac,
        "has_suggestions": usuario.has_suggestions,
        "has_evaluations": usuario.has_evaluations
    }