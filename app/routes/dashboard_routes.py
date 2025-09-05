# app/routes/dashboard_routes.py

from flask import Blueprint, jsonify
from app.decorators.auth_decorators import admin_required
from app.services import dashboard_service

dashboard_bp = Blueprint('dashboard_bp', __name__)

@dashboard_bp.route('/summary', methods=['GET'])
@admin_required()
def get_dashboard_summary():
    """
    [ADMIN] Retorna dados resumidos para o painel principal.
    """
    summary_data = dashboard_service.get_summary_data()
    if summary_data is None:
        return jsonify({"mensagem": "Erro ao buscar dados do dashboard."}), 500
    
    return jsonify(summary_data), 200