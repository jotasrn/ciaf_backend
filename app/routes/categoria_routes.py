from flask import Blueprint, request, jsonify
from app.decorators.auth_decorators import admin_required
from app.services import categoria_service
from bson import ObjectId, json_util
import json

categoria_bp = Blueprint('categoria_bp', __name__)

@categoria_bp.route('/<string:esporte_id>', methods=['GET'])
@admin_required()
def get_categorias(esporte_id):
    categorias = categoria_service.listar_categorias_por_esporte(esporte_id)
    return json.loads(json_util.dumps(categorias)), 200

@categoria_bp.route('/', methods=['POST'])
@admin_required()
def criar_nova_categoria():
    dados = request.get_json()
    if not dados or 'nome' not in dados or 'esporte_id' not in dados:
        return jsonify({"mensagem": "Nome e esporte_id são obrigatórios."}), 400
    try:
        categoria_service.criar_categoria(dados)
        return jsonify({"mensagem": "Categoria criada com sucesso!"}), 201
    except ValueError as e:
        return jsonify({"mensagem": str(e)}), 409

# TODO: Implementar rotas PUT e DELETE