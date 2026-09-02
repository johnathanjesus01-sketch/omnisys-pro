from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    nome = Column(String, default="")
    ramo = Column(String, default="geral")  # Ex: restaurante, odonto, loja, geral
    doc = Column(String, default="")  # CNPJ/CPF
    tel = Column(String, default="")  # Telefone/WhatsApp
    role = Column(String, default="usuario")  # adminMaster, admin, cliente, usuario
    ativo = Column(Boolean, default=True)

    # === PLANOS / SAAS ===
    plan_type = Column(String, default="basico")  # basico, intermediario, completo
    has_sac = Column(Boolean, default=False)
    has_suggestions = Column(Boolean, default=False)
    has_evaluations = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)


class Empresa(Base):
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    nome_fantasia = Column(String, index=True)
    cnpj = Column(String, unique=True, index=True)
    ramo = Column(String, default="geral")


class SyncData(Base):
    """Armazena o espelho (KV JSON) do localStorage de cada usuário no servidor."""

    __tablename__ = "sync_data"
    __table_args__ = (UniqueConstraint("user_id", name="uq_sync_user"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    data = Column(Text, default="{}")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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