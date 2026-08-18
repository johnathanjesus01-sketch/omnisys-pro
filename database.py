from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Cria o arquivo do banco de dados local chamado odonto.db
SQLALCHEMY_DATABASE_URL = "sqlite:///./odonto.db"

# Estabelece o motor que conversa com o banco
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Cria a fábrica de 'sessões' (como se fossem conexões para enviar/receber dados)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para criarmos as nossas tabelas depois
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()