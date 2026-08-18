from sqlalchemy import Column, Integer, String, Boolean,ForeignKey,DateTime,Float
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    # === NOVOS CAMPOS DO SAAS ===
    # Nível de acesso (adminMaster, admin, cliente)
    role = Column(String, default="cliente")

    # Planos (basico, intermediario, completo)
    plan_type = Column(String, default="basico")

    # Liberação de Abas Dinâmicas
    has_sac = Column(Boolean, default=False)
    has_suggestions = Column(Boolean, default=False)
    has_evaluations = Column(Boolean, default=False)

class Empresa(Base):
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, index=True)
    nome_fantasia = Column(String, index=True)
    cnpj = Column(String, unique=True, index=True)
    ramo = Column(String, default="geral")  # Ex: odonto, oficina, petshop, loja

class ProdutoEstoque(Base):
    __tablename__ = "estoque"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"))
    nome = Column(String, index=True)
    quantidade = Column(Integer, default=0)
    preco_unitario = Column(Float, default=0.0)

class Atividade(Base):
    __tablename__ = "atividades"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"))
    titulo = Column(String, index=True)
    descricao = Column(String, nullable=True)
    status = Column(String, default="a_fazer")  # "a_fazer" ou "concluida"

class TransacaoFinanceira(Base):
    __tablename__ = "faturamento"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"))
    descricao = Column(String)
    valor = Column(Float)
    tipo = Column(String)  # "receita" ou "despesa"
    data = Column(DateTime, default=datetime.utcnow)
