# app/__init__.py 
import os
import re
import pytz
from flask import Flask, request
from flask_pymongo import PyMongo
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv

# Carrega variáveis do .env logo no início
load_dotenv()

mongo = PyMongo()
jwt = JWTManager()
timezone = None  # será configurado dentro de criar_app


def criar_app():
    app = Flask(__name__)

    # Configurações do app a partir do .env
    app.config["MONGO_URI"] = os.getenv("MONGO_URI")
    # Tenta pegar JWT_SECRET_KEY primeiro, senão usa SECRET_KEY
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY")
    app.config["TIMEZONE"] = os.getenv("TIMEZONE", "America/Sao_Paulo")

    if not app.config["MONGO_URI"] or not app.config["JWT_SECRET_KEY"]:
        raise ValueError("MONGO_URI e JWT_SECRET_KEY (ou SECRET_KEY) devem ser definidos no arquivo .env")

    # Configuração do CORS
    origins = [
        re.compile(r"http://localhost:\d+"),  # regex para qualquer porta local
        "https://ciaf-gestao.netlify.app"
    ]
    CORS(
        app,
        resources={r"/api/*": {"origins": origins}},
        supports_credentials=True,
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )

    # Inicializa extensões
    mongo.init_app(app)
    jwt.init_app(app)

    # Configura timezone global
    global timezone
    timezone = pytz.timezone(app.config["TIMEZONE"])

    # Trata pré-flight requests (CORS OPTIONS)
    @app.before_request
    def handle_preflight_requests():
        if request.method.upper() == "OPTIONS":
            return app.make_response(""), 200

    # Registra rotas
    with app.app_context():
        from .routes.health_check import health_check_bp
        from .routes.auth_routes import auth_bp
        from .routes.usuario_routes import usuario_bp
        from .routes.esporte_routes import esporte_bp
        from .routes.turma_routes import turma_bp
        from .routes.aula_routes import aula_bp
        from .routes.dashboard_routes import dashboard_bp
        from .routes.categoria_routes import categoria_bp
        from .routes.presenca_routes import presenca_bp

        app.register_blueprint(health_check_bp, url_prefix="/api")
        app.register_blueprint(auth_bp, url_prefix="/api/auth")
        app.register_blueprint(usuario_bp, url_prefix="/api/usuarios")
        app.register_blueprint(esporte_bp, url_prefix="/api/esportes")
        app.register_blueprint(turma_bp, url_prefix="/api/turmas")
        app.register_blueprint(aula_bp, url_prefix="/api/aulas")
        app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
        app.register_blueprint(categoria_bp, url_prefix="/api/categorias")
        app.register_blueprint(presenca_bp, url_prefix="/api/presencas")

    return app
