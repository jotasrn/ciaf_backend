from flask import Blueprint, request, jsonify
from app.decorators.auth_decorators import admin_required
from app.services import categoria_service
from bson import ObjectId, json_util
import json

categoria_bp = Blueprint('categoria_bp', __name__)

@categoria_bp.before_request
def handle_categoria_preflight():
    if request.method.upper() == 'OPTIONS':
        return '', 204

@categoria_bp.route('/', methods=['GET', 'OPTIONS'])
@admin_required()
def get_categorias():
    """
    [ADMIN] Lista todas as categorias.
    Pode ser filtrado por esporte_id (opcional).
    """
    esporte_id = request.args.get('esporte_id')
    if esporte_id:
        categorias = categoria_service.listar_categorias_por_esporte(esporte_id)
    else:
        categorias = categoria_service.listar_todas_categorias()
        
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

@categoria_bp.route('/<string:categoria_id>', methods=['PUT'])
@admin_required()
def atualizar_categoria_existente(categoria_id):
    dados = request.get_json()
    try:
        categoria_service.atualizar_categoria(categoria_id, dados)
        return jsonify({"mensagem": "Categoria atualizada com sucesso!"}), 200
    except ValueError as e:
        return jsonify({"mensagem": str(e)}), 400

@categoria_bp.route('/<string:categoria_id>', methods=['DELETE'])
@admin_required()
def deletar_categoria_existente(categoria_id):
    try:
        categoria_service.deletar_categoria(categoria_id)
        return '', 204 # No Content
    except ValueError as e:
        return jsonify({"mensagem": str(e)}), 400

