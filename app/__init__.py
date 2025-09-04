from flask import Flask
from flask_pymongo import PyMongo
from flask_cors import CORS
from flask_jwt_extended import JWTManager # Importar
from config import Config
import pytz

mongo = PyMongo()
timezone = None

def criar_app():
    """
    Cria e configura uma instância da aplicação Flask (Application Factory).
    """
    app = Flask(__name__)
    app.config.from_object(Config)

    # Renomeamos a chave de configuração do Flask-PyMongo para evitar conflitos
    # A flask-jwt-extended também usa 'JWT_SECRET_KEY', então vamos ser explícitos.
    app.config["JWT_SECRET_KEY"] = app.config["SECRET_KEY"]

    CORS(app, resources={r"/api/*": {"origins": "*"}})
    mongo.init_app(app)
    
    # Inicializa o JWTManager
    jwt = JWTManager(app)

    global timezone
    timezone = pytz.timezone(app.config['TIMEZONE'])

    with app.app_context():
        # Importar e registrar os novos blueprints
        from .routes.health_check import health_check_bp
        from .routes.auth_routes import auth_bp
        from .routes.usuario_routes import usuario_bp
        from .routes.turma_routes import turma_bp
        from .routes.aula_routes import aula_bp
        from .routes.esporte_routes import esporte_bp
        from .routes.presenca_routes import presenca_bp

        app.register_blueprint(health_check_bp, url_prefix='/api')
        app.register_blueprint(auth_bp, url_prefix='/api/auth')
        app.register_blueprint(usuario_bp, url_prefix='/api/usuarios')
        app.register_blueprint(turma_bp, url_prefix='/api/turmas')
        app.register_blueprint(aula_bp, url_prefix='/api/aulas')
        app.register_blueprint(esporte_bp, url_prefix='/api/esportes')
        app.register_blueprint(presenca_bp, url_prefix='/api/presencas')

    return app