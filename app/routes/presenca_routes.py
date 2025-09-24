from flask import Blueprint, request, jsonify
from app.services import presenca_service
# Importa os decorators corretos e os utilitários de BSON
from app.decorators.auth_decorators import admin_required, role_required
from flask_jwt_extended import get_jwt_identity
from bson import json_util
import json

presenca_bp = Blueprint('presenca_bp', __name__)


# Rota que você já tinha (para editar uma presença específica)
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
        # Supondo que seu serviço se chama 'atualizar_presenca'
        modificados = presenca_service.atualizar_presenca(presenca_id, dados, admin_id)
        if modificados > 0:
            return jsonify({"mensagem": "Registro de presença atualizado com sucesso."}), 200
        else:
            return jsonify({"mensagem": "Nenhuma alteração realizada ou registro não encontrado."}), 404
    except ValueError as e:
        return jsonify({"mensagem": str(e)}), 400


# --- ROTA FALTANTE ADICIONADA AQUI ---
@presenca_bp.route('/aula/<string:aula_id>', methods=['GET'])
@role_required(roles=['admin', 'professor'])
def get_presencas_por_aula(aula_id):
    """
    [ADMIN, PROFESSOR] Obtém a lista de chamada (alunos e status) para uma aula específica.
    """
    try:
        # A função já existe no seu serviço, só precisamos chamá-la
        lista_chamada = presenca_service.obter_presencas_por_aula(aula_id)
        # Usamos json_util para garantir que os dados do MongoDB sejam convertidos para JSON corretamente
        return json.loads(json_util.dumps(lista_chamada)), 200
    except ValueError as e:
        return jsonify({"mensagem": str(e)}), 400
    except Exception as e:
        return jsonify({"mensagem": "Erro interno ao buscar lista de chamada.", "detalhes": str(e)}), 500