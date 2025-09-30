# app/__init__.py 
import os
import re
import pytz
from flask import Flask
from flask_pymongo import PyMongo
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()

mongo = PyMongo()
jwt = JWTManager()
timezone = None

def criar_app():
    app = Flask(__name__)

    # Configurações do app
    app.config["MONGO_URI"] = os.getenv("MONGO_URI")
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY")
    app.config["TIMEZONE"] = os.getenv("TIMEZONE", "America/Sao_Paulo")

    if not app.config["MONGO_URI"] or not app.config["JWT_SECRET_KEY"]:
        raise ValueError("MONGO_URI e JWT_SECRET_KEY devem ser definidos no arquivo .env")

    # --- CORREÇÃO PRINCIPAL: Configuração de CORS simplificada ---
    # Apenas a configuração da extensão Flask-CORS é necessária.
    # Ela lida com as requisições OPTIONS automaticamente.
    origins = [
        "http://localhost:5173", # Para desenvolvimento local
        "https://ciaf-gestao.netlify.app"  # Para produção
    ]
    CORS(
        app,
        resources={r"/api/*": {"origins": origins}},
        supports_credentials=True
    )

    # Inicializa extensões
    mongo.init_app(app)
    jwt.init_app(app)

    # Configura timezone global
    global timezone
    timezone = pytz.timezone(app.config["TIMEZONE"])

    # A função @app.before_request para OPTIONS foi REMOVIDA daqui.

    # Registra rotas
    with app.app_context():
        from .routes import (
            health_check, auth_routes, usuario_routes, esporte_routes,
            turma_routes, aula_routes, dashboard_routes, categoria_routes,
            presenca_routes
        )

        app.register_blueprint(health_check.health_check_bp, url_prefix="/api")
        app.register_blueprint(auth_bp, url_prefix="/api/auth")
        app.register_blueprint(usuario_bp, url_prefix="/api/usuarios")
        app.register_blueprint(esporte_bp, url_prefix="/api/esportes")
        app.register_blueprint(turma_bp, url_prefix="/api/turmas")
        app.register_blueprint(aula_bp, url_prefix="/api/aulas")
        app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
        app.register_blueprint(categoria_bp, url_prefix="/api/categorias")
        app.register_blueprint(presenca_bp, url_prefix="/api/presencas")

    return app