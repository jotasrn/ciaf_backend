from flask import Blueprint, jsonify
from app import mongo
import datetime
from app import timezone

# Cria um Blueprint. "health_check_bp" é o nome do blueprint.
health_check_bp = Blueprint('health_check_bp', __name__)

@health_check_bp.route('/health', methods=['GET'])
def health_check():
    """
    Verifica a saúde da API e a conexão com o banco de dados.
    """
    try:
        # O comando 'ping' é uma forma leve de verificar a conexão com o MongoDB
        mongo.db.command('ping')
        status_db = "conectado"
    except Exception as e:
        status_db = f"erro: {e}"

    agora = datetime.datetime.now(timezone).strftime('%d/%m/%Y %H:%M:%S')

    return jsonify({
        "status_api": "operacional",
        "status_banco_dados": status_db,
        "timestamp_servidor": agora,
        "timezone_servidor": str(timezone)
    }), 200