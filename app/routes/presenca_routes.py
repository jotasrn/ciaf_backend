from flask import Blueprint, request, jsonify
from app.services import presenca_service
from app.decorators.auth_decorators import admin_required
from flask_jwt_extended import get_jwt_identity

presenca_bp = Blueprint('presenca_bp', __name__)

@presenca_bp.route('/<string:presenca_id>', methods=['PUT'])
@admin_required()
def atualizar_registro_presenca(presenca_id):
    """
    [ADMIN] Endpoint para editar um registro de presença existente.
    """
    dados = request.get_json()
    if not dados:
        return jsonify({"mensagem": "Corpo da requisição não pode ser vazio."}), 400

    admin_id = get_jwt_identity()

    try:
        modificados = presenca_service.atualizar_presenca(presenca_id, dados, admin_id)
        if modificados > 0:
            return jsonify({"mensagem": "Registro de presença atualizado com sucesso."}), 200
        else:
            return jsonify({"mensagem": "Nenhuma alteração realizada ou registro não encontrado."}), 404
    except ValueError as e:
        return jsonify({"mensagem": str(e)}), 400