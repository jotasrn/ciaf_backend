import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

class Config:
    """Configurações base da aplicação."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'uma-chave-secreta-padrao-caso-nao-exista')
    MONGO_URI = os.getenv('MONGO_URI')
    TIMEZONE = os.getenv('TIMEZONE', 'UTC')
    
    # Validação pragmática: garantir que a URI do Mongo foi definida
    if not MONGO_URI:
        raise ValueError("A variável de ambiente MONGO_URI não foi definida.")