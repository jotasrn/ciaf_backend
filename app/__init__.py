from flask import Flask
from flask_pymongo import PyMongo
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config
import pytz

# Inicialização das extensões
mongo = PyMongo()
timezone = None

def criar_app():
    """
    Cria e configura uma instância da aplicação Flask (Application Factory).
    """
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Chave secreta para JWT
    app.config["JWT_SECRET_KEY"] = app.config["SECRET_KEY"]

    # Configuração de CORS para permitir acesso do frontend
    origins = [
        "http://localhost:53763", # Portas de desenvolvimento do Flutter
        "https://ciaf-gestao.netlify.app" # URL de produção do seu site
    ]
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Inicialização das extensões com a aplicação
    mongo.init_app(app)
    jwt = JWTManager(app)

    # Configuração do timezone global da aplicação
    global timezone
    timezone = pytz.timezone(app.config['TIMEZONE'])


    with app.app_context():
        # Importar e registrar os blueprints (módulos de rotas)
        from .routes.health_check import health_check_bp
        from .routes.auth_routes import auth_bp
        from .routes.usuario_routes import usuario_bp
        from .routes.esporte_routes import esporte_bp
        from .routes.turma_routes import turma_bp
        from .routes.aula_routes import aula_bp
        from .routes.dashboard_routes import dashboard_bp
        from .routes.categoria_routes import categoria_bp 

        app.register_blueprint(health_check_bp, url_prefix='/api')
        app.register_blueprint(auth_bp, url_prefix='/api/auth')
        app.register_blueprint(usuario_bp, url_prefix='/api/usuarios')
        app.register_blueprint(esporte_bp, url_prefix='/api/esportes')
        app.register_blueprint(turma_bp, url_prefix='/api/turmas')
        app.register_blueprint(aula_bp, url_prefix='/api/aulas')
        app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
        app.register_blueprint(categoria_bp, url_prefix='/api/categorias')

    return app