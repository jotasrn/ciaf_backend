from flask import Flask
from flask_pymongo import PyMongo
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config
import pytz

mongo = PyMongo()
timezone = None

def criar_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["JWT_SECRET_KEY"] = app.config["SECRET_KEY"]


    origins = [
        r"http://localhost:.*", # Para desenvolvimento local
        "https://ciaf-gestao.netlify.app" # URL de produção
    ]
    CORS(app, resources={r"/api/*": {"origins": origins}}, supports_credentials=True)

    mongo.init_app(app)
    jwt = JWTManager(app)

    global timezone
    timezone = pytz.timezone(app.config['TIMEZONE'])

    with app.app_context():
        # Imports e registros dos blueprints...
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